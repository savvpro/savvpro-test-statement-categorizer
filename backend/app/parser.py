"""Reads messy CSV statements into RawTransaction rows.

Handles:
- different header names (Date / Transaction Date / Posted, Description / Details / Memo ...)
- a single signed Amount column, or separate Debit / Credit columns
- "$1,234.56", "(45.00)", "45.00 CR", "-45.00", "45.00-" amount styles
- several date formats
- preamble lines before the header, blank rows and "Total"/"Balance" summary rows
Rows that cannot be read are reported, never silently dropped.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .models import Kind, RawTransaction

DATE_HEADERS = {"date", "transaction date", "trans date", "posted", "posted date", "posting date"}
DESC_HEADERS = {"description", "details", "memo", "narrative", "payee", "merchant", "transaction"}
AMOUNT_HEADERS = {"amount", "amount (usd)", "transaction amount", "value"}
DEBIT_HEADERS = {"debit", "withdrawal", "withdrawals", "money out", "charges"}
CREDIT_HEADERS = {"credit", "deposit", "deposits", "money in", "payments"}

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%Y/%m/%d")
SUMMARY_ROW = re.compile(r"^\s*(total|opening balance|closing balance|balance forward|statement balance)\b", re.I)


class StatementFormatError(ValueError):
    """The file is not a statement we can read at all."""


@dataclass
class ParseResult:
    transactions: list[RawTransaction] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)  # {"row": n, "error": "..."}


def parse_date(value: str) -> date:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date '{value}'")


def parse_amount(value: str) -> Decimal | None:
    """Returns a signed Decimal (negative = money out style), or None if empty."""
    v = (value or "").strip()
    if not v:
        return None
    negative = False
    if v.startswith("(") and v.endswith(")"):
        negative, v = True, v[1:-1]
    upper = v.upper()
    if upper.endswith("CR"):
        v = v[:-2]
    elif upper.endswith("DR"):
        negative, v = True, v[:-2]
    v = v.strip()
    if v.endswith("-"):
        negative, v = True, v[:-1]
    if v.startswith("-"):
        negative, v = not negative, v[1:]
    v = v.replace("$", "").replace(",", "").replace("USD", "").strip()
    try:
        amount = Decimal(v)
    except InvalidOperation as exc:
        raise ValueError(f"unrecognised amount '{value}'") from exc
    return -amount if negative else amount


def _find_header(rows: list[list[str]]) -> int:
    for i, row in enumerate(rows[:15]):
        names = {c.strip().lower() for c in row}
        if names & DATE_HEADERS and names & DESC_HEADERS:
            return i
    raise StatementFormatError("Could not find a header row with a date and a description column.")


def _col(header: list[str], options: set[str]) -> int | None:
    for i, name in enumerate(header):
        if name.strip().lower() in options:
            return i
    return None


def parse_csv(content: bytes | str) -> ParseResult:
    text = content.decode("utf-8-sig", errors="replace") if isinstance(content, bytes) else content
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise StatementFormatError("The file is empty.")

    h = _find_header(rows)
    header = rows[h]
    date_i, desc_i = _col(header, DATE_HEADERS), _col(header, DESC_HEADERS)
    amt_i = _col(header, AMOUNT_HEADERS)
    deb_i, cred_i = _col(header, DEBIT_HEADERS), _col(header, CREDIT_HEADERS)
    if amt_i is None and deb_i is None and cred_i is None:
        raise StatementFormatError("Could not find an Amount (or Debit/Credit) column.")

    result = ParseResult()
    for offset, row in enumerate(rows[h + 1:], start=h + 2):  # 1-based file line numbers
        if not any(c.strip() for c in row):
            continue
        cell = lambda i: row[i].strip() if i is not None and i < len(row) else ""  # noqa: E731
        desc = " ".join(cell(desc_i).split())
        if SUMMARY_ROW.match(desc) or SUMMARY_ROW.match(cell(date_i)):
            continue
        try:
            tx_date = parse_date(cell(date_i))
            if amt_i is not None:
                signed = parse_amount(cell(amt_i))
                if signed is None:
                    raise ValueError("missing amount")
            else:
                debit, credit = parse_amount(cell(deb_i)), parse_amount(cell(cred_i))
                if debit is None and credit is None:
                    raise ValueError("missing amount")
                signed = (credit or Decimal(0)) - abs(debit or Decimal(0))
            if signed == 0:
                raise ValueError("zero amount")
            if not desc:
                raise ValueError("missing description")
        except ValueError as exc:
            result.errors.append({"row": offset, "error": str(exc)})
            continue
        kind = Kind.CREDIT if signed > 0 else Kind.DEBIT
        result.transactions.append(RawTransaction(offset, tx_date, desc, abs(signed), kind))
    return result
