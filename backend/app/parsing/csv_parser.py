"""Tolerant CSV statement reader.

Real exports are messy: preamble lines before the header, different column names,
separate debit/credit columns, mixed date formats, currency symbols, thousands
separators, accounting-style negatives and junk rows (blank lines, "Total" lines).

The parser never guesses silently: rows it cannot read are skipped and reported as
warnings with their line number, and file-level problems raise ``CSVParseError``.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

from dateutil import parser as date_parser
from pydantic import BaseModel, Field

HEADER_SCAN_LINES = 15

DATE_ALIASES = [
    "transaction date",
    "txn date",
    "trans date",
    "date",
    "posting date",
    "posted date",
    "post date",
    "value date",
]
DESCRIPTION_ALIASES = [
    "description",
    "details",
    "transaction details",
    "merchant",
    "merchant name",
    "payee",
    "narrative",
    "memo",
    "name",
]
AMOUNT_ALIASES = ["amount", "transaction amount", "value"]
DEBIT_ALIASES = ["debit", "debits", "withdrawal", "withdrawals", "money out", "debit amount"]
CREDIT_ALIASES = ["credit", "credits", "deposit", "deposits", "money in", "credit amount"]
CURRENCY_ALIASES = ["currency", "ccy", "currency code"]

CURRENCY_SYMBOLS = "$€£¥₹"
CURRENCY_CODES = ("USD", "EUR", "GBP", "PKR", "CAD", "AUD", "INR", "AED", "JPY", "RS")

SLASH_DATE = re.compile(r"^\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\s*$")
ISO_DATE = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$")


class CSVParseError(ValueError):
    """The file as a whole cannot be read. The message is safe to show to users."""


class RawTransaction(BaseModel):
    row_number: int = Field(description="Line number in the original file (1-based)")
    date: date
    description: str
    amount: float = Field(description="Signed: negative = money out, positive = money in")
    currency: str = "USD"
    notes: list[str] = Field(default_factory=list)


class ParseResult(BaseModel):
    transactions: list[RawTransaction]
    warnings: list[str] = Field(default_factory=list)
    date_order: str = Field(description="'month-first' or 'day-first' for slash dates")


class ColumnMap(BaseModel):
    date: int
    description: int
    amount: int | None = None
    debit: int | None = None
    credit: int | None = None
    currency: int | None = None


# --------------------------------------------------------------------------- helpers


def _norm_header(value: str) -> str:
    value = re.sub(r"\(.*?\)", " ", value.lower())  # "Amount (USD)" -> "amount"
    value = re.sub(r"[^a-z ]+", " ", value)
    return " ".join(value.split())


def _find(headers: list[str], aliases: list[str]) -> int | None:
    """Index of the first header matching an alias; aliases are in priority order."""
    for alias in aliases:
        for index, header in enumerate(headers):
            if header == alias:
                return index
    return None


def _map_columns(raw_headers: list[str]) -> ColumnMap | None:
    headers = [_norm_header(h) for h in raw_headers]
    date_col = _find(headers, DATE_ALIASES)
    desc_col = _find(headers, DESCRIPTION_ALIASES)
    amount_col = _find(headers, AMOUNT_ALIASES)
    debit_col = _find(headers, DEBIT_ALIASES)
    credit_col = _find(headers, CREDIT_ALIASES)
    if date_col is None or desc_col is None:
        return None
    if amount_col is None and debit_col is None and credit_col is None:
        return None
    return ColumnMap(
        date=date_col,
        description=desc_col,
        amount=amount_col,
        debit=debit_col if amount_col is None else None,
        credit=credit_col if amount_col is None else None,
        currency=_find(headers, CURRENCY_ALIASES),
    )


def _decode(content: bytes | str) -> str:
    if isinstance(content, str):
        return content
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CSVParseError("Could not read the file encoding")  # pragma: no cover


def _dialect(text: str) -> type[csv.Dialect] | csv.Dialect:
    sample = "\n".join(text.splitlines()[: HEADER_SCAN_LINES + 5])
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def parse_amount(value: str | None) -> float | None:
    """Turn a messy amount string into a signed float. Empty -> None, junk -> ValueError.

    Handles: "1,250.00", "$54.99", "$-48.20", "(54.99)", "54.99-", "54.99 CR", "+30.00".
    """
    if value is None:
        return None
    text = value.strip().upper()
    if not text:
        return None

    sign = 1
    if text.endswith(" CR") or text.endswith("CR"):
        text = text[:-2].strip()
    elif text.endswith(" DR") or text.endswith("DR"):
        sign = -1
        text = text[:-2].strip()
    if text.startswith("(") and text.endswith(")"):
        sign = -sign
        text = text[1:-1].strip()

    for code in CURRENCY_CODES:
        text = text.replace(code, "")
    text = text.strip(CURRENCY_SYMBOLS + " ")
    if text.endswith("-"):
        sign = -sign
        text = text[:-1]
    text = text.replace(",", "").replace(" ", "")
    for symbol in CURRENCY_SYMBOLS:
        text = text.replace(symbol, "")

    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", text):
        raise ValueError(f"'{value.strip()}' is not a number")
    return round(sign * float(text), 2)


def detect_date_order(values: list[str]) -> tuple[str, bool]:
    """Decide whether slash dates like 03/05/2026 are month-first or day-first.

    Looks at the whole file: any first part > 12 proves day-first, any second part > 12
    proves month-first. Returns (order, ambiguous) where ambiguous means no proof found.
    """
    day_first_evidence = month_first_evidence = False
    saw_slash_date = False
    for value in values:
        match = SLASH_DATE.match(value or "")
        if not match:
            continue
        saw_slash_date = True
        first, second = int(match.group(1)), int(match.group(2))
        if first > 12 >= second:
            day_first_evidence = True
        elif second > 12 >= first:
            month_first_evidence = True
    if day_first_evidence and not month_first_evidence:
        return "day-first", False
    if month_first_evidence and not day_first_evidence:
        return "month-first", False
    return "month-first", saw_slash_date


def parse_date(value: str, day_first: bool) -> date:
    text = value.strip()
    if not text:
        raise ValueError("date is missing")
    iso = ISO_DATE.match(text)
    if iso:  # dateutil's dayfirst would turn 2026-05-03 into 5 March, so handle ISO ourselves
        try:
            return date(*(int(part) for part in iso.groups()))
        except ValueError as exc:
            raise ValueError(f"'{text}' is not a valid date") from exc
    try:
        parsed = date_parser.parse(text, dayfirst=day_first, fuzzy=False)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"'{text}' is not a date") from exc
    return parsed.date()


# --------------------------------------------------------------------------- main entry


def parse_statement(content: bytes | str) -> ParseResult:
    """Parse a CSV statement into signed transactions plus row-level warnings."""
    text = _decode(content)
    if not text.strip():
        raise CSVParseError("The file is empty")

    rows = list(csv.reader(io.StringIO(text), _dialect(text)))

    header_index = None
    columns = None
    for index, row in enumerate(rows[:HEADER_SCAN_LINES]):
        columns = _map_columns(row)
        if columns is not None:
            header_index = index
            break
    if columns is None or header_index is None:
        headers = [_norm_header(h) for h in (rows[0] if rows else [])]
        if _find(headers, DATE_ALIASES) is None:
            raise CSVParseError("Could not find a date column (expected e.g. 'Date' or 'Txn Date')")
        if _find(headers, DESCRIPTION_ALIASES) is None:
            raise CSVParseError(
                "Could not find a description column (expected e.g. 'Description' or 'Details')"
            )
        raise CSVParseError(
            "Could not find an amount column (expected 'Amount' or 'Debit' and 'Credit')"
        )

    data_rows = [
        (header_index + offset + 2, row)  # +2: 1-based line numbers, and skip the header
        for offset, row in enumerate(rows[header_index + 1 :])
    ]
    data_rows = [(line, row) for line, row in data_rows if any(cell.strip() for cell in row)]
    if not data_rows:
        raise CSVParseError("No transactions found in the file")

    date_values = [row[columns.date] for _, row in data_rows if len(row) > columns.date]
    date_order, ambiguous = detect_date_order(date_values)
    day_first = date_order == "day-first"

    warnings: list[str] = []
    if ambiguous:
        warnings.append(
            "Dates like 03/05/2026 are ambiguous in this file; they were read as month/day"
        )

    transactions: list[RawTransaction] = []
    for line, row in data_rows:
        try:
            transactions.append(_parse_row(line, row, columns, day_first, ambiguous))
        except ValueError as exc:
            warnings.append(f"Row {line} skipped: {exc}")

    if not transactions:
        raise CSVParseError("No transactions found in the file")
    return ParseResult(transactions=transactions, warnings=warnings, date_order=date_order)


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _parse_row(
    line: int, row: list[str], columns: ColumnMap, day_first: bool, ambiguous: bool
) -> RawTransaction:
    notes: list[str] = []
    raw_date = _cell(row, columns.date)
    txn_date = parse_date(raw_date, day_first)

    description = " ".join(_cell(row, columns.description).split())
    if not description:
        raise ValueError("description is missing")
    if ambiguous and SLASH_DATE.match(raw_date):
        first, second = SLASH_DATE.match(raw_date).group(1, 2)  # type: ignore[union-attr]
        if int(first) <= 12 and int(second) <= 12 and first != second:
            notes.append(f"Date '{raw_date}' is ambiguous; read as month/day")

    if columns.amount is not None:
        amount = parse_amount(_cell(row, columns.amount))
        if amount is None:
            raise ValueError("amount is missing")
    else:
        debit = parse_amount(_cell(row, columns.debit))
        credit = parse_amount(_cell(row, columns.credit))
        if debit is None and credit is None:
            raise ValueError("both debit and credit are empty")
        if debit is not None and credit is not None and debit and credit:
            notes.append("Row had both a debit and a credit; used credit minus debit")
        amount = round(abs(credit or 0.0) - abs(debit or 0.0), 2)

    currency = (_cell(row, columns.currency) or "USD").upper()
    return RawTransaction(
        row_number=line,
        date=txn_date,
        description=description,
        amount=amount,
        currency=currency,
        notes=notes,
    )
