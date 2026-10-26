"""CSV parser for credit card statements.

Handles single Amount column vs Debit/Credit columns, header variants,
date/amount parsing, duplicates, edge cases, and sign convention.
"""

import csv
import io
import math
import re
from datetime import date, datetime
from typing import Optional

DATE_HEADERS = {
    "date", "posting date", "transaction date", "posted date",
    "transactiondate", "postingdate",
}
DESCRIPTION_HEADERS = {
    "description", "details", "memo", "payee", "transaction",
}
AMOUNT_HEADERS = {"amount"}
DEBIT_HEADERS = {"debit", "charges", "payments out", "paymentout"}
CREDIT_HEADERS = {"credit", "deposits", "payments in", "paymentin"}

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
US_DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
AMOUNT_RE = re.compile(r"^[\$]?\s*\(?([\d,]+\.?\d*)\)?\s*$")


def _normalize_header(header: str) -> str:
    return header.strip().lower()


def _detect_column_type(header: str) -> Optional[str]:
    h = _normalize_header(header)
    if h in DATE_HEADERS:
        return "date"
    if h in DESCRIPTION_HEADERS:
        return "description"
    if h in AMOUNT_HEADERS:
        return "amount"
    if h in DEBIT_HEADERS:
        return "debit"
    if h in CREDIT_HEADERS:
        return "credit"
    return None


def _parse_date(raw: str) -> Optional[date]:
    raw = raw.strip()
    if not raw:
        return None
    if ISO_DATE_RE.match(raw):
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None
    if US_DATE_RE.match(raw):
        try:
            return datetime.strptime(raw, "%m/%d/%Y").date()
        except ValueError:
            return None
    return None


def _parse_amount(raw: str) -> Optional[float]:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    cleaned = raw.replace("$", "").replace(",", "").strip()
    is_paren_negative = cleaned.startswith("(") and cleaned.endswith(")")
    if is_paren_negative:
        cleaned = cleaned[1:-1].strip()
    is_explicit_negative = cleaned.startswith("-")
    if is_explicit_negative:
        cleaned = cleaned[1:].strip()
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    if is_paren_negative or is_explicit_negative:
        value = -abs(value)
    return value

def _apply_sign_convention(amount: Optional[float], column_type: str) -> Optional[float]:
    if amount is None:
        return None
    if column_type == "debit":
        return -abs(amount)
    if column_type == "credit":
        return abs(amount)
    return amount



def parse_csv(file_content: bytes) -> dict:
    """Parse an uploaded CSV statement file.

    Args:
        file_content: Raw bytes of the CSV file.

    Returns:
        dict with keys:
            - transactions: list of dicts (date, description, amount, is_duplicate, row_number)
            - warnings: list of human-readable warning strings
    """
    text = file_content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))

    rows = list(reader)
    if not rows:
        return {"transactions": [], "warnings": ["Empty file"]}

    header = [h.strip() for h in rows[0]]
    col_types = [_detect_column_type(h) for h in header]

    has_date = "date" in col_types
    has_description = "description" in col_types
    has_amount = "amount" in col_types
    has_debit = "debit" in col_types
    has_credit = "credit" in col_types
    has_debit_credit = has_debit and has_credit

    if not has_date:
        return {"transactions": [], "warnings": ["No date column found in header"]}
    if not has_description:
        return {"transactions": [], "warnings": ["No description column found in header"]}
    if not has_amount and not has_debit_credit:
        return {
            "transactions": [],
            "warnings": ["No amount or debit/credit columns found in header"],
        }

    date_idx = col_types.index("date")
    desc_idx = col_types.index("description")
    amount_idx = col_types.index("amount") if has_amount else None
    debit_idx = col_types.index("debit") if has_debit else None
    credit_idx = col_types.index("credit") if has_credit else None

    transactions: list[dict] = []
    warnings: list[str] = []
    seen_keys: set = set()

    for row_num, row in enumerate(rows[1:], start=2):
        if not row or all(cell.strip() == "" for cell in row):
            warnings.append(f"Row {row_num}: empty row skipped")
            continue

        def get_cell(idx: Optional[int]) -> str:
            if idx is None or idx >= len(row):
                return ""
            return row[idx].strip()

        raw_date = get_cell(date_idx)
        raw_desc = get_cell(desc_idx)

        parsed_date = _parse_date(raw_date)
        if parsed_date is None:
            warnings.append(f"Row {row_num}: unparseable date '{raw_date}', skipped")
            continue

        description = raw_desc
        if not description:
            warnings.append(f"Row {row_num}: blank description")

        if has_amount:
            raw_amount = get_cell(amount_idx)
            parsed_amount = _parse_amount(raw_amount)
            if parsed_amount is None:
                warnings.append(
                    f"Row {row_num}: unparseable amount '{raw_amount}', skipped"
                )
                continue
            amount = _apply_sign_convention(parsed_amount, "amount")
        else:
            raw_debit = get_cell(debit_idx)
            raw_credit = get_cell(credit_idx)

            debit_val = _parse_amount(raw_debit) if raw_debit else None
            credit_val = _parse_amount(raw_credit) if raw_credit else None

            if debit_val is not None and credit_val is not None:
                warnings.append(
                    f"Row {row_num}: both debit and credit present, using debit"
                )
                amount = -abs(debit_val)
            elif debit_val is not None:
                amount = -abs(debit_val)
            elif credit_val is not None:
                amount = abs(credit_val)
            else:
                warnings.append(f"Row {row_num}: no amount found, skipped")
                continue

        upper_desc = description.upper()
        if any(kw in upper_desc for kw in ("FOREIGN", "CURRENCY", "FX")):
            warnings.append(
                f"Row {row_num}: possible foreign currency transaction: {description}"
            )

        row_key = (parsed_date.isoformat(), description, amount)
        is_duplicate = row_key in seen_keys
        seen_keys.add(row_key)
        if is_duplicate:
            warnings.append(f"Row {row_num}: duplicate transaction detected")

        transactions.append(
            {
                "date": parsed_date.isoformat(),
                "description": description,
                "amount": amount,
                "is_duplicate": is_duplicate,
                "row_number": row_num,
            }
        )

    return {"transactions": transactions, "warnings": warnings}
