"""Strict CSV boundary: validate the complete file before storing any transactions."""

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
CURRENCIES = ("USD", "PKR", "EUR", "GBP", "CAD", "AUD")
ALIASES = {
    "transaction_date": "date",
    "posting_date": "date",
    "posted_date": "date",
    "details": "description",
    "narration": "description",
    "memo": "description",
    "transaction_description": "description",
    "withdrawal": "debit",
    "withdrawals": "debit",
    "deposit": "credit",
    "deposits": "credit",
    "id": "transaction_id",
    "reference": "transaction_id",
}


class StatementError(ValueError):
    """A user-correctable file error, safe to display in the UI."""


@dataclass(frozen=True)
class RawTransaction:
    date: str
    description: str
    amount_cents: int
    source_id: str
    row_number: int
    duplicate_of: int | None = None


@dataclass(frozen=True)
class ParsedStatement:
    currency: str
    transactions: list[RawTransaction]


def _amount(value: str) -> int:
    text = value.strip()
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", text):
        raise StatementError("Invalid amount. Use numbers such as -59.99 or 1,234.56.")
    decimal = Decimal(text.replace(",", ""))
    if decimal.as_tuple().exponent < -2:
        raise StatementError("Use at most two decimal places for amounts.")
    if abs(decimal) > 999_999_999:
        raise StatementError("The amount exceeds the supported limit of 999,999,999.")
    return int(decimal * 100)


def _date(value: str, date_format: str) -> str:
    formats = {
        "ISO": (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
        "DMY": (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y"),
        "MDY": (r"\d{2}/\d{2}/\d{4}", "%m/%d/%Y"),
    }
    pattern, fmt = formats[date_format]
    try:
        if not re.fullmatch(pattern, value):
            raise ValueError
        return datetime.strptime(value, fmt).date().isoformat()
    except ValueError as exc:
        raise StatementError(
            f"Invalid date '{value[:30]}'. Check the selected date format."
        ) from exc


def parse_csv(
    content: bytes,
    *,
    currency: str = "USD",
    date_format: str = "ISO",
    amount_convention: str = "negative_expense",
) -> ParsedStatement:
    if len(content) > MAX_BYTES:
        raise StatementError("File exceeds the 5 MB limit.")
    if currency not in CURRENCIES:
        raise StatementError("Unsupported currency.")
    if date_format not in ("ISO", "DMY", "MDY"):
        raise StatementError("Unsupported date format.")
    if amount_convention not in ("negative_expense", "positive_expense"):
        raise StatementError("Unsupported amount convention.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StatementError("Save the CSV using UTF-8 encoding and try again.") from exc
    if "\x00" in text:
        raise StatementError("The file contains invalid binary content. Upload a UTF-8 CSV.")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    transactions = []
    fingerprints: dict[tuple, int] = {}
    source_ids: dict[str, int] = {}
    detected_currency = None
    try:
        headers = next(reader, [])
        headers = [re.sub(r"[\s-]+", "_", h.strip().lower()) for h in headers]
        headers = [ALIASES.get(h, h) for h in headers]
        if len(set(headers)) != len(headers):
            raise StatementError("The file has duplicate column names or aliases.")
        for required in ("date", "description"):
            if required not in headers:
                raise StatementError(f"Missing '{required}' column.")
        has_amount = "amount" in headers
        has_split = "debit" in headers and "credit" in headers
        if not has_amount and not has_split:
            raise StatementError("Add an 'amount' column, or both 'debit' and 'credit' columns.")
        if has_amount and ("debit" in headers or "credit" in headers):
            raise StatementError("Use either amount or debit/credit columns, not both.")
        for values in reader:
            if not values or all(not v.strip() for v in values):
                continue
            row_number = reader.line_num
            if len(transactions) >= MAX_ROWS:
                raise StatementError("Files may contain at most 10,000 transactions.")
            try:
                if len(values) != len(headers):
                    raise StatementError("The number of columns does not match the header.")
                row = dict(zip(headers, (v.strip() for v in values), strict=True))
                description = row["description"]
                if not description or len(description) > 500:
                    raise StatementError("The description must contain 1–500 characters.")
                source_id = row.get("transaction_id", "")
                if len(source_id) > 100:
                    raise StatementError("Transaction IDs must be at most 100 characters.")
                date = _date(row["date"], date_format)
                row_currency = row.get("currency", "").upper() or currency
                if row_currency not in CURRENCIES:
                    raise StatementError(
                        "Unsupported currency. Use USD, PKR, EUR, GBP, CAD or AUD."
                    )
                if detected_currency and detected_currency != row_currency:
                    raise StatementError(
                        "Mixed currency files are not supported. Split by currency."
                    )
                detected_currency = row_currency
                if has_amount:
                    amount = _amount(row["amount"])
                    if amount_convention == "positive_expense":
                        amount = -amount
                else:
                    debit = _amount(row["debit"]) if row["debit"] else 0
                    credit = _amount(row["credit"]) if row["credit"] else 0
                    if debit < 0 or credit < 0 or (debit and credit):
                        raise StatementError("Use one nonnegative debit or credit per row.")
                    amount = credit - debit
                if amount == 0:
                    raise StatementError("A zero amount is not a transaction; remove this row.")
                fingerprint = (date, " ".join(description.upper().split()), amount)
                duplicate_of = source_ids.get(source_id) if source_id else None
                duplicate_of = duplicate_of or fingerprints.get(fingerprint)
                fingerprints.setdefault(fingerprint, row_number)
                if source_id:
                    source_ids.setdefault(source_id, row_number)
                transactions.append(
                    RawTransaction(
                        date,
                        description,
                        amount,
                        source_id,
                        row_number,
                        duplicate_of,
                    )
                )
            except StatementError as exc:
                raise StatementError(f"Row {row_number}: {exc}") from exc
    except csv.Error as exc:
        raise StatementError(f"Invalid CSV near row {reader.line_num}: {exc}.") from exc
    if not transactions:
        raise StatementError("The CSV contains no transactions.")
    return ParsedStatement(detected_currency or currency, transactions)
