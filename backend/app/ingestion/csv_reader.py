"""Tolerant CSV statement reader.

Real bank exports disagree on almost everything: header names, date formats,
a single signed amount column vs separate money-in / money-out columns,
currency symbols, thousands separators and accounting-style negatives.
Bad rows are reported as issues instead of failing the whole upload.
"""
import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

from ..domain.errors import StatementError
from ..domain.models import ParsedStatement, ParseIssue, RawTransaction

DATE_HEADERS = ("date", "transaction date", "posting date", "posted date", "value date")
DESC_HEADERS = ("description", "details", "merchant", "narrative", "payee", "memo", "transaction")
AMOUNT_HEADERS = ("amount", "value", "transaction amount")
OUT_HEADERS = ("debit", "money out", "paid out", "withdrawal", "out")
IN_HEADERS = ("credit", "money in", "paid in", "deposit", "in")

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d %b %Y", "%d %B %Y", "%d-%b-%Y")


def parse_amount(value: str) -> Optional[Decimal]:
    """Parse '£1,234.50', '(12.00)', '-12', '12.00 CR', '12.00 DR'. Empty -> None."""
    text = (value or "").strip().upper()
    if not text:
        return None
    sign = 1
    if text.startswith("(") and text.endswith(")"):
        sign, text = -1, text[1:-1]
    if text.endswith("DR"):
        sign, text = -1, text[:-2]
    elif text.endswith("CR"):
        text = text[:-2]
    text = re.sub(r"[£$€,\s]", "", text)
    if text.startswith("-"):
        sign, text = -sign, text[1:]
    elif text.startswith("+"):
        text = text[1:]
    try:
        return sign * Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Unreadable amount '{value}'")


def parse_date(value: str) -> date:
    text = (value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unreadable date '{value}'")


def _find_column(headers: Dict[str, str], candidates: Tuple[str, ...]) -> Optional[str]:
    return next((headers[c] for c in candidates if c in headers), None)


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1")


class CsvStatementReader:
    extensions = (".csv",)

    def __init__(self, max_rows: int = 10_000):
        self._max_rows = max_rows

    def read(self, content: bytes) -> ParsedStatement:
        text = _decode(content)
        if not text.strip():
            raise StatementError("The file is empty.")

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise StatementError("No header row found.")
        headers = {h.strip().lower(): h for h in reader.fieldnames if h}
        columns = self._resolve_columns(headers)

        transactions: List[RawTransaction] = []
        issues: List[ParseIssue] = []
        for row_number, record in enumerate(reader, start=2):  # row 1 is the header
            if row_number - 1 > self._max_rows:
                raise StatementError(f"Statement has more than {self._max_rows} rows.")
            if not any((v or "").strip() for v in record.values() if isinstance(v, str)):
                continue  # blank line
            try:
                transactions.append(self._parse_row(row_number, record, columns))
            except ValueError as exc:
                issues.append(ParseIssue(row=row_number, message=str(exc)))

        if not transactions and not issues:
            raise StatementError("The statement has no transactions.")
        return ParsedStatement(transactions=transactions, issues=issues)

    @staticmethod
    def _resolve_columns(headers: Dict[str, str]) -> Dict[str, Optional[str]]:
        columns = {
            "date": _find_column(headers, DATE_HEADERS),
            "description": _find_column(headers, DESC_HEADERS),
            "amount": _find_column(headers, AMOUNT_HEADERS),
            "out": _find_column(headers, OUT_HEADERS),
            "in": _find_column(headers, IN_HEADERS),
        }
        if not columns["date"] or not columns["description"]:
            raise StatementError("Could not find a date and a description column.")
        if not columns["amount"] and not (columns["out"] or columns["in"]):
            raise StatementError("Could not find an amount column (or money in / money out columns).")
        return columns

    @staticmethod
    def _parse_row(row_number: int, record: Dict[str, str], columns: Dict[str, Optional[str]]) -> RawTransaction:
        description = " ".join((record.get(columns["description"]) or "").split())
        if not description:
            raise ValueError("Missing description")
        if columns["amount"]:
            amount = parse_amount(record.get(columns["amount"]) or "")
        else:
            money_out = parse_amount(record.get(columns["out"]) or "") if columns["out"] else None
            money_in = parse_amount(record.get(columns["in"]) or "") if columns["in"] else None
            if money_out and money_in:
                raise ValueError("Row has both money in and money out")
            amount = -abs(money_out) if money_out else money_in
        if amount is None:
            raise ValueError("Missing amount")
        if amount == 0:
            raise ValueError("Zero-value row skipped")
        return RawTransaction(
            row=row_number,
            date=parse_date(record.get(columns["date"]) or ""),
            description=description,
            amount=amount,
        )
