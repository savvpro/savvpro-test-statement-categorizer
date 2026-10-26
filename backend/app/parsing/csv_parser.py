"""Read a bank-statement CSV into RawTransaction rows.

Handles different header names, signed-amount or debit/credit layouts,
several date formats, and messy amounts. A bad row is reported in
`errors`; it never stops the rest of the file from loading.
"""
import csv
import datetime as dt
import io
import re
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel

from app.models import RawTransaction

DATE_HEADERS = {"date", "posting date", "post date", "transaction date", "trans date"}
DESC_HEADERS = {"description", "details", "memo", "payee", "narrative", "transaction description"}
AMOUNT_HEADERS = {"amount", "transaction amount"}
DEBIT_HEADERS = {"debit", "debits", "withdrawal", "withdrawals", "money out"}
CREDIT_HEADERS = {"credit", "credits", "deposit", "deposits", "money in"}

# Order matters: slashes are read as US month/day/year.
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%b %d, %Y")


class StatementFormatError(ValueError):
    """The file as a whole cannot be understood (missing columns, empty...)."""


class RowError(BaseModel):
    row_number: int
    message: str


class ParseResult(BaseModel):
    transactions: list[RawTransaction]
    errors: list[RowError]


def parse_date(text: str) -> dt.date:
    text = text.strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {text!r}")


def parse_amount(text: str) -> Decimal:
    """'$1,234.50' -> 1234.50, '(12.00)' -> -12.00, '12.00-' -> -12.00."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("empty amount")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = re.sub(r"[()$,\s]", "", cleaned)
    if cleaned.endswith("-"):
        negative = True
        cleaned = cleaned[:-1]
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"not a number: {text!r}") from None
    if not value.is_finite():
        raise ValueError(f"not a number: {text!r}")
    return -abs(value) if negative else value


def _find(headers: list[str], aliases: set[str]) -> int | None:
    for index, header in enumerate(headers):
        if header in aliases:
            return index
    return None


def _decode(content: str | bytes) -> str:
    if isinstance(content, str):
        return content
    try:
        return content.decode("utf-8-sig")  # also strips an Excel BOM
    except UnicodeDecodeError:
        return content.decode("latin-1")


def parse_statement(content: str | bytes) -> ParseResult:
    reader = csv.reader(io.StringIO(_decode(content)))

    header_row = next((row for row in reader if any(c.strip() for c in row)), None)
    if header_row is None:
        raise StatementFormatError("The file is empty.")

    headers = [h.strip().lower() for h in header_row]
    date_col = _find(headers, DATE_HEADERS)
    desc_col = _find(headers, DESC_HEADERS)
    amount_col = _find(headers, AMOUNT_HEADERS)
    debit_col = _find(headers, DEBIT_HEADERS)
    credit_col = _find(headers, CREDIT_HEADERS)

    has_amount = amount_col is not None or debit_col is not None or credit_col is not None
    if date_col is None or desc_col is None or not has_amount:
        raise StatementFormatError(
            "Could not find the required columns (date, description, and "
            f"amount or debit/credit). Found: {header_row}"
        )

    transactions: list[RawTransaction] = []
    errors: list[RowError] = []

    for row in reader:
        if not any(cell.strip() for cell in row):
            continue  # blank line
        line = reader.line_num
        try:
            needed = [c for c in (date_col, desc_col, amount_col, debit_col, credit_col) if c is not None]
            if len(row) <= max(needed):
                raise ValueError("row has too few columns")

            description = " ".join(row[desc_col].split())
            if not description:
                raise ValueError("empty description")

            if amount_col is not None:
                amount = parse_amount(row[amount_col])
            else:
                debit_text = row[debit_col] if debit_col is not None else ""
                credit_text = row[credit_col] if credit_col is not None else ""
                if not debit_text.strip() and not credit_text.strip():
                    raise ValueError("no debit or credit amount")
                debit = parse_amount(debit_text) if debit_text.strip() else Decimal(0)
                credit = parse_amount(credit_text) if credit_text.strip() else Decimal(0)
                # abs(): some banks print debits as negatives, some as positives.
                amount = abs(credit) - abs(debit)

            transactions.append(
                RawTransaction(
                    row_number=line,
                    date=parse_date(row[date_col]),
                    description=description,
                    amount=amount,
                )
            )
        except ValueError as exc:
            errors.append(RowError(row_number=line, message=str(exc)))

    return ParseResult(transactions=transactions, errors=errors)