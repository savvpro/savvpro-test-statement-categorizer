"""Read messy credit-card and bank CSV exports into outflow-signed rows.

Internal amount sign: positive means money out, negative means money in.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

DATE_ALIASES = [
    "posted date",
    "posting date",
    "post date",
    "transaction date",
    "trans date",
    "processed date",
    "date",
]
DESCRIPTION_ALIASES = [
    "description",
    "transaction description",
    "merchant",
    "memo",
    "narrative",
    "details",
    "name",
    "desc",
]
AMOUNT_ALIASES = ["amount", "amount usd", "transaction amount", "amt", "value"]
DEBIT_ALIASES = ["debit", "withdrawal", "money out", "charge", "charges"]
CREDIT_ALIASES = ["credit", "deposit", "money in"]
TYPE_ALIASES = ["transaction type", "type"]

MONEY_OUT_TYPES = {"sale", "purchase", "debit", "pos", "charge"}
MONEY_IN_TYPES = {"return", "refund", "credit", "payment", "reversal", "deposit"}

TOTAL_LABELS = {
    "total",
    "totals",
    "total debits",
    "total credits",
    "ending balance",
    "beginning balance",
    "opening balance",
}


class ParseError(Exception):
    """The file is not a statement we can read."""


@dataclass
class ParsedRow:
    row_number: int
    date: str | None
    description: str
    amount: Decimal
    pending: bool


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    direction_source: str = "amount"


def parse_statement(text: str, account_type: str = "credit_card") -> ParseResult:
    if account_type not in {"credit_card", "bank"}:
        raise ParseError("Account type must be credit_card or bank.")

    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")

    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines[:25]):
        if line.strip() and _looks_like_header(line):
            header_index = index
            break
    if header_index is None:
        raise ParseError(
            "No header row found. The file needs a date column, a description column, "
            "and an amount column (or debit and credit columns)."
        )

    body = "\n".join(lines[header_index:])
    reader = csv.reader(io.StringIO(body), dialect=_sniff_dialect(body))
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise ParseError("The file has a header but no transactions.") from exc

    date_col = _find_column(headers, DATE_ALIASES)
    description_col = _find_column(headers, DESCRIPTION_ALIASES)
    amount_col = _find_column(headers, AMOUNT_ALIASES)
    debit_col = _find_column(headers, DEBIT_ALIASES)
    credit_col = _find_column(headers, CREDIT_ALIASES)
    type_col = _find_column(headers, TYPE_ALIASES)

    if date_col is None or description_col is None:
        raise ParseError("The header needs a date column and a description column.")
    if amount_col is None and debit_col is None and credit_col is None:
        raise ParseError("The header needs an amount column, or debit and credit columns.")

    use_split = debit_col is not None or credit_col is not None
    result = ParseResult(direction_source="debit_credit" if use_split else account_type)
    if use_split:
        result.warnings.append("Used the debit and credit columns to decide money in versus money out.")

    for offset, cells in enumerate(reader, start=2):
        row_number = header_index + offset
        if not any(cell.strip() for cell in cells):
            continue
        description = _cell(cells, description_col)
        date_text = _cell(cells, date_col)
        if _is_total_row(description) or _is_total_row(date_text):
            result.warnings.append(f"Row {row_number}: ignored a totals or balance line.")
            continue
        try:
            amount = _row_amount(
                cells,
                amount_col=amount_col,
                debit_col=debit_col,
                credit_col=credit_col,
                type_col=type_col,
                use_split=use_split,
                account_type=account_type,
            )
        except (ValueError, InvalidOperation):
            result.warnings.append(f"Row {row_number}: skipped because the amount is not a number.")
            continue

        parsed_date = _parse_date(date_text) if date_text else None
        if date_text and parsed_date is None:
            result.warnings.append(f"Row {row_number}: skipped because the date could not be read ({date_text!r}).")
            continue

        result.rows.append(
            ParsedRow(
                row_number=row_number,
                date=parsed_date,
                description=description.strip(),
                amount=amount.quantize(Decimal("0.01")),
                pending=bool(re.search(r"\bPENDING\b", description.upper())),
            )
        )

    if not result.rows:
        raise ParseError("No transactions were left after reading the file.")
    if len(result.rows) > 5000:
        raise ParseError("This file has more than 5000 transactions. Split it and upload the parts.")
    return result


def _sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample[:4096], delimiters=",;\t")
    except csv.Error:
        return csv.excel


def _looks_like_header(line: str) -> bool:
    for delimiter in (",", ";", "\t"):
        try:
            cells = next(csv.reader([line], delimiter=delimiter))
        except csv.Error:
            continue
        if _header_cells(cells):
            return True
    return False


def _header_cells(cells: list[str]) -> bool:
    norms = [_norm_header(cell) for cell in cells]
    has_date = any(cell in DATE_ALIASES for cell in norms)
    has_description = any(cell in DESCRIPTION_ALIASES for cell in norms)
    has_money = any(cell in AMOUNT_ALIASES or cell in DEBIT_ALIASES or cell in CREDIT_ALIASES for cell in norms)
    return has_date and has_description and has_money


def _find_column(headers: list[str], aliases: list[str]) -> int | None:
    norms = [_norm_header(header) for header in headers]
    for alias in aliases:
        for index, header in enumerate(norms):
            if header == alias:
                return index
    return None


def _norm_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _cell(cells: list[str], index: int | None) -> str:
    if index is None or index >= len(cells):
        return ""
    return cells[index].strip()


def _is_total_row(description: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", description.lower()).strip()
    return normalized in TOTAL_LABELS or normalized.startswith("total ")


def _parse_date(value: str) -> str | None:
    text = value.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    month_first = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", text)
    day_first = re.fullmatch(r"(\d{1,2})[-/ ]([A-Za-z]+)[-/ ](\d{4})", text)
    if month_first:
        month_name, day, year = month_first.groups()
        return _iso_date(year, month_name, day)
    if day_first:
        day, month_name, year = day_first.groups()
        return _iso_date(year, month_name, day)
    return None


def _iso_date(year: str, month_name: str, day: str) -> str | None:
    month = _MONTHS.get(month_name.lower())
    if month is None:
        return None
    try:
        return datetime(int(year), month, int(day)).date().isoformat()
    except ValueError:
        return None


def _row_amount(
    cells: list[str],
    *,
    amount_col: int | None,
    debit_col: int | None,
    credit_col: int | None,
    type_col: int | None,
    use_split: bool,
    account_type: str,
) -> Decimal:
    if use_split:
        debit = _optional_amount(_cell(cells, debit_col))
        credit = _optional_amount(_cell(cells, credit_col))
        if debit == 0 and credit == 0 and amount_col is not None and _cell(cells, amount_col):
            return _signed_amount(_cell(cells, amount_col), _cell(cells, type_col), account_type)
        return (abs(debit) - abs(credit)).quantize(Decimal("0.01"))
    return _signed_amount(_cell(cells, amount_col), _cell(cells, type_col), account_type)


def _optional_amount(raw: str) -> Decimal:
    if not raw:
        return Decimal("0")
    value, _hint = _parse_amount(raw)
    return value


def _signed_amount(raw: str, type_word: str, account_type: str) -> Decimal:
    written, hint = _parse_amount(raw)
    kind = re.sub(r"[^a-z]+", " ", type_word.lower()).strip()
    if kind in MONEY_IN_TYPES:
        return -abs(written)
    if kind in MONEY_OUT_TYPES:
        return abs(written)
    if hint == "cr":
        return -abs(written)
    if hint == "dr":
        return abs(written)
    if account_type == "bank":
        return -written
    return written


def _parse_amount(raw: str) -> tuple[Decimal, str | None]:
    text = raw.strip()
    if not text:
        raise ValueError("empty amount")
    hint = None
    upper = text.upper()
    for suffix, name in ((" CR", "cr"), (" DR", "dr"), ("CR", "cr"), ("DR", "dr")):
        if upper.endswith(suffix):
            candidate = text[: -len(suffix)].strip()
            if candidate:
                hint = name
                text = candidate
                upper = text.upper()
                break
    trailing_minus = text.endswith("-")
    if trailing_minus:
        text = text[:-1].strip()
    negative = "(" in text and ")" in text
    text = text.replace("$", "").replace(",", "").replace("(", "").replace(")", "").strip()
    if text.startswith("+"):
        text = text[1:]
    if not text:
        raise ValueError("empty amount")
    value = Decimal(text)
    if negative or trailing_minus:
        value = -abs(value)
    return value, hint
