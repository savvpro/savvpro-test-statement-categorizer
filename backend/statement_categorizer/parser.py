"""Strict CSV adapters. Reject the entire import rather than silently drop bad rows."""

import csv
import io
import re
import unicodedata
from datetime import datetime
from decimal import Decimal

from .domain import CURRENCIES, AmountMode, DateFormat, ImportOptions, ParsedTransaction

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000
MAX_AMOUNT_MINOR = 100_000_000_00  # Bound arithmetic / accidental extra zeros.

ALIASES = {
    "date": {"date", "transaction date", "posted date", "posting date"},
    "description": {"description", "merchant", "details", "memo"},
    "amount": {"amount", "transaction amount"},
    "debit": {"debit", "debits", "withdrawal", "withdrawals"},
    "credit": {"credit", "credits", "deposit", "deposits"},
    "currency": {"currency", "currency code"},
    "status": {"status", "transaction status"},
}


class StatementError(ValueError):
    def __init__(self, message: str, errors: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []


def parse_money(value: str, currency: str) -> int:
    """Accept exact two-decimal dot notation; never round malformed amounts."""
    value = value.strip().replace("\u00a0", " ")
    if not value:
        raise ValueError("Amount is required.")
    if len(value) > 32:
        raise ValueError("Amount text is too long; check the exported number.")
    parenthesized = value.startswith("(") and value.endswith(")")
    if parenthesized:
        value = value[1:-1].strip()
    negative = value.startswith("-")
    explicit_sign = value.startswith(("-", "+"))
    if explicit_sign:
        value = value[1:].strip()
    if parenthesized and explicit_sign:
        raise ValueError("Use a minus sign OR parentheses, not both.")
    # Symbols are accepted only when consistent with the chosen statement currency.
    symbols = {"USD": "$", "CAD": "$", "AUD": "$", "GBP": "£", "EUR": "€", "PKR": "₨"}
    prefix = currency if value.startswith(currency) else symbols[currency]
    if value.startswith(prefix):
        value = value[len(prefix) :].strip()
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?", value):
        raise ValueError("Use dot decimals, optional grouped commas, and at most two decimal places.")
    minor = int(Decimal(value.replace(",", "")) * 100)
    if minor > MAX_AMOUNT_MINOR:
        raise ValueError("Amount exceeds the supported limit (100,000,000).")
    return -minor if negative or parenthesized else minor


def parse_date(value: str, date_format: DateFormat) -> str:
    formats = {
        DateFormat.ISO: (r"[0-9]{4}-[0-9]{2}-[0-9]{2}", "%Y-%m-%d"),
        DateFormat.DMY: (r"[0-9]{2}/[0-9]{2}/[0-9]{4}", "%d/%m/%Y"),
        DateFormat.MDY: (r"[0-9]{2}/[0-9]{2}/[0-9]{4}", "%m/%d/%Y"),
    }
    pattern, fmt = formats[date_format]
    if not re.fullmatch(pattern, value):
        raise ValueError(f"Date must match {fmt.replace('%', '')}; select the correct date format.")
    try:
        return datetime.strptime(value, fmt).date().isoformat()
    except ValueError as error:
        raise ValueError("Date is not a valid calendar date.") from error


def _columns(headers: list[str], mode: AmountMode) -> dict[str, int]:
    normalized = [re.sub(r"[\s_]+", " ", h.strip().lower()) for h in headers]
    if len(set(normalized)) != len(normalized) or any(not h for h in normalized):
        raise StatementError("CSV headers must be nonempty and unique.")
    result = {}
    for target, aliases in ALIASES.items():
        matches = [i for i, header in enumerate(normalized) if header in aliases]
        if len(matches) > 1:
            raise StatementError(f"Multiple columns map to {target}; use one unambiguous column.")
        if matches:
            result[target] = matches[0]
    required = {"date", "description"} | ({"debit", "credit"} if mode == AmountMode.SPLIT else {"amount"})
    missing = sorted(required - result.keys())
    if missing:
        raise StatementError("Missing columns for selected amount format: " + ", ".join(missing))
    if "amount" in result and ("debit" in result or "credit" in result):
        raise StatementError("Amount and debit/credit columns coexist. Remove the unused amount columns first.")
    return result


def parse_statement(content: bytes, options: ImportOptions) -> list[ParsedTransaction]:
    if options.currency not in CURRENCIES:
        raise StatementError("Unsupported currency; choose a supported two-decimal currency.")
    if not content or len(content) > MAX_FILE_BYTES:
        raise StatementError("Upload a nonempty CSV no larger than 5 MiB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise StatementError("Save your CSV as UTF-8 and try again.") from error
    if "\x00" in text:
        raise StatementError("The file contains null bytes; upload a UTF-8 CSV.")
    # Sniff only the header: multiline merchant fields cannot confuse delimiter choice.
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
        reader = csv.reader(io.StringIO(text, newline=""), dialect=dialect, strict=True)
        headers = next(reader)
    except (csv.Error, StopIteration, IndexError) as error:
        raise StatementError("Could not read a CSV header. Use comma, semicolon, or tab separation.") from error
    columns = _columns(headers, options.amount_mode)
    transactions, errors = [], []
    count = 0
    try:
        while True:
            source_row = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            if not row or not any(cell.strip() for cell in row):
                continue
            count += 1
            if count > MAX_ROWS:
                raise StatementError(f"A statement may contain at most {MAX_ROWS:,} transactions.")
            try:
                if len(row) != len(headers):
                    raise ValueError("Row width differs from the header; quote amounts containing commas.")
                get = lambda key: row[columns[key]].strip() if key in columns else ""  # noqa: E731
                description = get("description")
                if not description or len(description) > 500:
                    raise ValueError("Description must contain 1–500 characters.")
                if any(unicodedata.category(c).startswith("C") and c not in "\n\r\t" for c in description):
                    raise ValueError("Description contains unsupported control characters.")
                currency = get("currency").upper() or options.currency
                if currency != options.currency:
                    raise ValueError(f"Currency must be {options.currency}; import each currency separately.")
                if options.amount_mode == AmountMode.SPLIT:
                    debit = parse_money(get("debit"), currency) if get("debit") else 0
                    credit = parse_money(get("credit"), currency) if get("credit") else 0
                    if not get("debit") and not get("credit"):
                        raise ValueError("A debit or credit amount is required.")
                    if min(debit, credit) < 0 or (debit != 0 and credit != 0):
                        raise ValueError("Debit and credit must be nonnegative; only one may be nonzero.")
                    amount = credit - debit
                else:
                    amount = parse_money(get("amount"), currency)
                    if options.amount_mode == AmountMode.CARD:
                        amount = -amount
                status = get("status").lower()
                if status not in {"", "posted", "settled", "completed", "pending"}:
                    raise ValueError("Status must be posted, settled, completed, or pending.")
                transactions.append(
                    ParsedTransaction(
                        source_row,
                        parse_date(get("date"), options.date_format),
                        description,
                        amount,
                        currency,
                        status == "pending",
                    )
                )
            except ValueError as error:
                errors.append({"row": source_row, "message": str(error)})
                if len(errors) >= 100:
                    break
    except csv.Error as error:
        raise StatementError("CSV quoting is invalid.", [{"row": reader.line_num, "message": str(error)}]) from error
    if errors:
        raise StatementError("Nothing was imported. Fix these rows and upload again (up to 100 errors shown).", errors)
    if not transactions:
        raise StatementError("The CSV contains no transactions.")
    return transactions
