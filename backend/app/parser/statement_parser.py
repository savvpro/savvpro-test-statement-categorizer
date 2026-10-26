"""Parse bank/credit card statement exports (CSV) into normalized transactions."""

from __future__ import annotations

import csv
import io
import re
import uuid
from dataclasses import dataclass

from app.models import Transaction


DATE_ALIASES = ("date", "transaction date", "posting date", "posted date", "trans date")
DESC_ALIASES = (
    "description",
    "memo",
    "merchant",
    "payee",
    "details",
    "transaction description",
    "name",
)
AMOUNT_ALIASES = ("amount", "transaction amount", "debit", "charge")
CREDIT_ALIASES = ("credit", "payment", "deposit")


@dataclass
class _ColumnMap:
    date: int | None = None
    description: int | None = None
    amount: int | None = None
    debit: int | None = None
    credit: int | None = None


def _normalize_header(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.strip().lower())


def _find_column(headers: list[str], aliases: tuple[str, ...]) -> int | None:
    for i, h in enumerate(headers):
        if h in aliases or any(a in h for a in aliases):
            return i
    return None


def _parse_amount(raw: str) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in ("", "nan", "none"):
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = s.replace("$", "").replace(",", "").strip()
    if s.startswith("-"):
        negative = True
        s = s[1:].strip()
    if s.startswith("+"):
        s = s[1:].strip()
    try:
        val = float(s)
    except ValueError:
        return None
    return -abs(val) if negative else val


def _detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample[:4096], delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def _locate_header_row(rows: list[list[str]]) -> int:
    for idx, row in enumerate(rows[:15]):
        if not row:
            continue
        headers = [_normalize_header(c) for c in row]
        has_date = _find_column(headers, DATE_ALIASES) is not None
        has_desc = _find_column(headers, DESC_ALIASES) is not None
        has_money = (
            _find_column(headers, AMOUNT_ALIASES) is not None
            or _find_column(headers, CREDIT_ALIASES) is not None
        )
        if has_date and has_desc and has_money:
            return idx
    return 0


def _build_column_map(headers: list[str]) -> _ColumnMap:
    norm = [_normalize_header(h) for h in headers]
    return _ColumnMap(
        date=_find_column(norm, DATE_ALIASES),
        description=_find_column(norm, DESC_ALIASES),
        amount=_find_column(norm, AMOUNT_ALIASES),
        debit=_find_column(norm, ("debit", "withdrawal", "charge")),
        credit=_find_column(norm, CREDIT_ALIASES),
    )


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _row_amount(row: list[str], cols: _ColumnMap) -> tuple[float | None, str]:
    if cols.amount is not None:
        raw = _cell(row, cols.amount)
        parsed = _parse_amount(raw)
        if parsed is not None:
            return parsed, raw

    debit_raw = _cell(row, cols.debit) if cols.debit is not None else ""
    credit_raw = _cell(row, cols.credit) if cols.credit is not None else ""

    debit = _parse_amount(debit_raw) if debit_raw else None
    credit = _parse_amount(credit_raw) if credit_raw else None

    if debit is not None and debit != 0:
        val = -abs(debit) if debit > 0 else debit
        return val, debit_raw
    if credit is not None and credit != 0:
        val = abs(credit)
        return val, credit_raw
    return None, ""


def parse_statement_csv(content: bytes | str) -> list[Transaction]:
    if isinstance(content, bytes):
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content

    delimiter = _detect_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = [row for row in reader if any(cell.strip() for cell in row)]

    if not all_rows:
        raise ValueError("The file appears empty or has no readable rows.")

    header_idx = _locate_header_row(all_rows)
    headers = all_rows[header_idx]
    cols = _build_column_map(headers)

    if cols.description is None:
        raise ValueError("Could not find a description column in the statement.")
    if cols.date is None:
        raise ValueError("Could not find a date column in the statement.")
    if cols.amount is None and cols.debit is None and cols.credit is None:
        raise ValueError("Could not find amount, debit, or credit columns.")

    transactions: list[Transaction] = []
    for row in all_rows[header_idx + 1 :]:
        desc = _cell(row, cols.description)
        date = _cell(row, cols.date)
        if not desc and not date:
            continue
        amount, raw_amount = _row_amount(row, cols)
        if amount is None:
            continue

        transactions.append(
            Transaction(
                id=str(uuid.uuid4()),
                date=date,
                description=desc,
                amount=amount,
                raw_amount=raw_amount,
            )
        )

    if not transactions:
        raise ValueError("No transactions could be parsed. Check column headers and formats.")

    return transactions
