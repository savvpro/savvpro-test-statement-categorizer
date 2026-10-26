"""
Flexible Bank & Credit Card Statement Parser.
Autodetects column layouts for Chase, Amex, Bank of America, Wells Fargo, Capital One, and generic CSVs.
"""

import csv
import io
import re
import uuid
from typing import List, Dict, Any, Optional

DATE_HEADERS = ["DATE", "TRANSACTION DATE", "POST DATE", "POSTING DATE", "TRANS DATE"]
DESC_HEADERS = ["DESCRIPTION", "NAME", "PAYEE", "MERCHANT", "MEMO", "DETAILS", "TRANSACTION"]
AMOUNT_HEADERS = ["AMOUNT", "TOTAL"]
DEBIT_HEADERS = ["DEBIT", "WITHDRAWAL", "EXPENSE", "CHARGE"]
CREDIT_HEADERS = ["CREDIT", "DEPOSIT", "PAYMENT"]


def clean_currency_amount(val: Any) -> float:
    """
    Parses currency strings like '$1,234.56', '-$45.00', '(50.00)', or '12.50CR'.
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if not s:
        return 0.0

    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1]
    elif s.endswith("-"):
        is_negative = True
        s = s[:-1]
    elif s.startswith("-"):
        is_negative = True
        s = s[1:]
    elif "CR" in s.upper():
        # Credit representation in some banks
        s = re.sub(r"CR", "", s, flags=re.IGNORECASE)

    # Remove dollar signs, commas, spaces
    s = re.sub(r"[\$,\s]", "", s)
    try:
        amount = float(s)
        return -amount if is_negative else amount
    except ValueError:
        return 0.0


def parse_statement_csv(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parses CSV content and extracts standardized transaction dictionaries.
    """
    # Use io.StringIO to read lines
    reader = csv.reader(io.StringIO(csv_content.strip()))
    rows = list(reader)
    if not rows:
        return []

    # Find the header row
    header_idx = -1
    date_col = -1
    desc_col = -1
    amount_col = -1
    debit_col = -1
    credit_col = -1

    for idx, row in enumerate(rows):
        normalized_row = [c.strip().upper() for c in row]
        # Check if this row looks like a header
        has_date = any(h in normalized_row for h in DATE_HEADERS)
        has_desc = any(h in normalized_row for h in DESC_HEADERS)
        if has_date and has_desc:
            header_idx = idx
            for col_i, col_name in enumerate(normalized_row):
                if col_name in DATE_HEADERS and date_col == -1:
                    date_col = col_i
                elif col_name in DESC_HEADERS and desc_col == -1:
                    desc_col = col_i
                elif col_name in AMOUNT_HEADERS and amount_col == -1:
                    amount_col = col_i
                elif col_name in DEBIT_HEADERS and debit_col == -1:
                    debit_col = col_i
                elif col_name in CREDIT_HEADERS and credit_col == -1:
                    credit_col = col_i
            break

    # If no header detected, fallback to column 0=date, 1=desc, 2=amount
    if header_idx == -1:
        date_col = 0
        desc_col = 1
        amount_col = 2
        data_rows = rows
    else:
        data_rows = rows[header_idx + 1:]

    transactions: List[Dict[str, Any]] = []

    for idx, row in enumerate(data_rows):
        if not row or not any(row):
            continue

        raw_date = row[date_col].strip() if date_col < len(row) else ""
        raw_desc = row[desc_col].strip() if desc_col < len(row) else ""

        # Skip header-like lines or empty descriptions
        if not raw_desc or raw_desc.upper() in DESC_HEADERS:
            continue

        amount = 0.0
        tx_type = "DEBIT"

        if debit_col != -1 or credit_col != -1:
            debit_val = row[debit_col].strip() if debit_col != -1 and debit_col < len(row) else ""
            credit_val = row[credit_col].strip() if credit_col != -1 and credit_col < len(row) else ""
            
            if debit_val:
                amount = -abs(clean_currency_amount(debit_val))
                tx_type = "DEBIT"
            elif credit_val:
                amount = abs(clean_currency_amount(credit_val))
                tx_type = "CREDIT"
        elif amount_col != -1 and amount_col < len(row):
            raw_amt = row[amount_col].strip()
            amount = clean_currency_amount(raw_amt)
            tx_type = "CREDIT" if amount > 0 else "DEBIT"

        transactions.append({
            "id": f"tx_{idx+1}_{uuid.uuid4().hex[:6]}",
            "date": raw_date,
            "raw_description": raw_desc,
            "amount": amount,
            "transaction_type": tx_type,
        })

    return transactions
