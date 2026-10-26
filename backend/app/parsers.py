"""
Statement parsers.

Currently supports clean CSV files with common column names.
"""

from __future__ import annotations

import csv
import io
from typing import Any


SUPPORTED_DATE_COLUMNS = {"date", "transaction date", "posted date", "trans date"}
SUPPORTED_DESC_COLUMNS = {"description", "memo", "payee", "merchant", "details", "narrative"}
SUPPORTED_AMOUNT_COLUMNS = {"amount", "transaction amount", "value", "debit", "credit"}


def _find_column(headers: list[str], candidates: set[str]) -> str | None:
    normalized = {h.strip().lower(): h for h in headers}
    for cand in candidates:
        if cand in normalized:
            return normalized[cand]
    return None


def parse_csv(content: str | bytes) -> list[dict[str, Any]]:
    """
    Parse a CSV statement into a list of transactions.

    Expected columns (case-insensitive, flexible names):
      - date
      - description / memo / payee
      - amount

    Returns list of dicts with keys: date, description, amount
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")  # handle BOM

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV has no headers")

    headers = list(reader.fieldnames)

    date_col = _find_column(headers, SUPPORTED_DATE_COLUMNS)
    desc_col = _find_column(headers, SUPPORTED_DESC_COLUMNS)
    amount_col = _find_column(headers, SUPPORTED_AMOUNT_COLUMNS)

    if not date_col or not desc_col or not amount_col:
        raise ValueError(
            f"Could not detect required columns. "
            f"Found headers: {headers}. "
            f"Need something like: date, description, amount"
        )

    transactions: list[dict[str, Any]] = []

    for i, row in enumerate(reader, start=2):  # 1-indexed + header
        raw_date = (row.get(date_col) or "").strip()
        raw_desc = (row.get(desc_col) or "").strip()
        raw_amount = (row.get(amount_col) or "").strip()

        if not raw_desc and not raw_amount:
            continue  # skip empty rows

        try:
            # Clean amount: remove $ , and handle parentheses for negatives
            cleaned = raw_amount.replace("$", "").replace(",", "").strip()
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = "-" + cleaned[1:-1]
            amount = float(cleaned)
        except ValueError:
            raise ValueError(f"Row {i}: cannot parse amount '{raw_amount}'")

        transactions.append(
            {
                "date": raw_date,
                "description": raw_desc,
                "amount": amount,
                "original_row": i,
            }
        )

    if not transactions:
        raise ValueError("No valid transactions found in the file")

    return transactions
