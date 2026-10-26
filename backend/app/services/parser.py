"""
Multi-format bank and credit card CSV statement parser.
Supports single-column amounts and split debit/credit columns,
auto-detects delimiters and column headers, and normalizes amounts.
"""

import csv
import io
import re
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from app.models.transaction import TransactionRaw


# Column synonym sets for flexible bank statement matching
DATE_COLUMNS = {
    "date", "transaction date", "posting date", "post date",
    "trans date", "posted", "effective date", "trans_date", "post_date"
}

DESC_COLUMNS = {
    "description", "merchant", "name", "memo", "transaction",
    "payee", "details", "narrative", "remarks", "trans_details",
    "transaction description"
}

AMOUNT_COLUMNS = {
    "amount", "transaction amount", "sum", "value", "net amount",
    "trans_amount", "total"
}

DEBIT_COLUMNS = {
    "debit", "withdrawal", "money out", "debit amount", "spend",
    "charge", "debits", "withdrawals"
}

CREDIT_COLUMNS = {
    "credit", "deposit", "money in", "credit amount", "received",
    "credits", "deposits"
}

TYPE_COLUMNS = {
    "type", "transaction type", "category", "trans type", "trans_type"
}

ACCOUNT_COLUMNS = {
    "account", "account number", "account name", "card", "card number"
}


def _clean_amount_str(val: Any) -> Optional[float]:
    """Parse string representation of currency amount into a signed float."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "-", ""):
        return None

    # Handle accounting parentheses: ($50.00) -> -50.00
    is_paren_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_paren_negative = True
        s = s[1:-1].strip()

    # Strip currency signs, whitespace, and thousands commas
    s = re.sub(r"[^\d.-]", "", s)
    if not s or s == "-":
        return None

    try:
        amount = float(s)
        if is_paren_negative and amount > 0:
            amount = -amount
        return round(amount, 2)
    except ValueError:
        return None


def _normalize_date_str(date_str: str) -> str:
    """Normalize various bank date formats into ISO standard YYYY-MM-DD."""
    cleaned = date_str.strip()
    formats_to_try = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m/%d/%y",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%b %d, %Y",
    ]
    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # If unrecognized format, return raw string
    return cleaned


def parse_csv(file_content: bytes, filename: str = "statement.csv") -> Tuple[List[TransactionRaw], List[str]]:
    """
    Parse a CSV statement file into a list of TransactionRaw models and warning messages.
    
    Returns:
        (transactions: List[TransactionRaw], warnings: List[str])
    """
    warnings: List[str] = []
    transactions: List[TransactionRaw] = []

    # 1. Decode bytes (try UTF-8 with BOM, standard UTF-8, then Latin-1)
    decoded_text: str
    try:
        decoded_text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded_text = file_content.decode("latin-1")
            warnings.append(f"File '{filename}' was decoded using Latin-1 fallback encoding.")
        except Exception as e:
            raise ValueError(f"Could not decode CSV file '{filename}': {str(e)}")

    if not decoded_text.strip():
        return [], ["File is completely empty."]

    # 2. Detect delimiter with csv.Sniffer fallback
    lines = [line for line in decoded_text.splitlines() if line.strip()]
    if not lines:
        return [], ["File contains no non-empty rows."]

    sample = "\n".join(lines[:10])
    delimiter = ","
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except Exception:
        # Fallback inspection: tab or comma or semicolon
        if "\t" in lines[0] and lines[0].count("\t") > lines[0].count(","):
            delimiter = "\t"
        elif ";" in lines[0] and lines[0].count(";") > lines[0].count(","):
            delimiter = ";"

    reader = csv.reader(io.StringIO(decoded_text), delimiter=delimiter)
    all_rows = list(reader)

    if not all_rows:
        return [], ["CSV file contains no rows."]

    # 3. Find and normalize header row
    header_idx = -1
    for idx, row in enumerate(all_rows):
        normalized_tokens = [col.strip().lower() for col in row if col.strip()]
        # Check if row looks like a header (contains at least one candidate for date, desc, or amount)
        has_date = any(t in DATE_COLUMNS for t in normalized_tokens)
        has_desc = any(t in DESC_COLUMNS for t in normalized_tokens)
        has_amt = any(t in (AMOUNT_COLUMNS | DEBIT_COLUMNS | CREDIT_COLUMNS) for t in normalized_tokens)
        if (has_date and has_desc) or (has_date and has_amt) or (has_desc and has_amt):
            header_idx = idx
            break

    if header_idx == -1:
        # Default to first non-empty row as header
        header_idx = 0

    header_row = [c.strip() for c in all_rows[header_idx]]
    data_rows = all_rows[header_idx + 1:]

    # Map column names
    col_map: Dict[str, int] = {}
    for idx, col_name in enumerate(header_row):
        norm = col_name.strip().lower()
        if norm in DATE_COLUMNS and "date" not in col_map:
            col_map["date"] = idx
        elif norm in DESC_COLUMNS and "description" not in col_map:
            col_map["description"] = idx
        elif norm in AMOUNT_COLUMNS and "amount" not in col_map:
            col_map["amount"] = idx
        elif norm in DEBIT_COLUMNS and "debit" not in col_map:
            col_map["debit"] = idx
        elif norm in CREDIT_COLUMNS and "credit" not in col_map:
            col_map["credit"] = idx
        elif norm in TYPE_COLUMNS and "type" not in col_map:
            col_map["type"] = idx
        elif norm in ACCOUNT_COLUMNS and "account" not in col_map:
            col_map["account"] = idx

    # Validate essential columns
    if "date" not in col_map:
        raise ValueError(
            f"Missing required 'date' column in '{filename}'. Found columns: {header_row}. "
            f"Expected one of: {sorted(list(DATE_COLUMNS))}"
        )
    if "description" not in col_map:
        raise ValueError(
            f"Missing required 'description' / 'merchant' column in '{filename}'. Found columns: {header_row}. "
            f"Expected one of: {sorted(list(DESC_COLUMNS))}"
        )

    has_amount = "amount" in col_map
    has_split = ("debit" in col_map) or ("credit" in col_map)
    if not has_amount and not has_split:
        raise ValueError(
            f"Missing amount columns in '{filename}'. Expected either an 'amount' column or 'debit'/'credit' columns. "
            f"Found: {header_row}"
        )

    if not data_rows:
        warnings.append("CSV file contains headers but no transaction rows.")
        return [], warnings

    # 4. Parse data rows
    for row_num, row in enumerate(data_rows, start=header_idx + 2):
        if not row or all(not str(c).strip() for c in row):
            continue

        # Extract date
        date_idx = col_map["date"]
        if date_idx >= len(row) or not row[date_idx].strip():
            warnings.append(f"Row {row_num}: Skipped due to missing date.")
            continue
        date_val = _normalize_date_str(row[date_idx].strip())

        # Extract description
        desc_idx = col_map["description"]
        if desc_idx >= len(row) or not row[desc_idx].strip():
            warnings.append(f"Row {row_num}: Skipped due to missing description.")
            continue
        raw_desc = row[desc_idx].strip()

        # Extract amount
        final_amount: Optional[float] = None

        if has_amount:
            amt_idx = col_map["amount"]
            if amt_idx < len(row):
                final_amount = _clean_amount_str(row[amt_idx])

        # If single amount column not present or empty, check split debit/credit
        if final_amount is None and has_split:
            debit_val: Optional[float] = None
            credit_val: Optional[float] = None

            if "debit" in col_map and col_map["debit"] < len(row):
                debit_val = _clean_amount_str(row[col_map["debit"]])
            if "credit" in col_map and col_map["credit"] < len(row):
                credit_val = _clean_amount_str(row[col_map["credit"]])

            if debit_val is not None and credit_val is not None:
                # Both present: credit is inflow (+), debit is outflow (-)
                final_amount = round(credit_val - debit_val, 2)
            elif debit_val is not None and debit_val != 0:
                final_amount = -abs(debit_val)
            elif credit_val is not None and credit_val != 0:
                final_amount = abs(credit_val)

        if final_amount is None:
            warnings.append(f"Row {row_num}: Skipped due to invalid/missing amount in row {row}.")
            continue

        # Optional metadata
        raw_type = None
        if "type" in col_map and col_map["type"] < len(row):
            raw_type = row[col_map["type"]].strip() or None

        account = None
        if "account" in col_map and col_map["account"] < len(row):
            account = row[col_map["account"]].strip() or None

        txn_id = f"TXN-{len(transactions) + 1:03d}"

        transactions.append(
            TransactionRaw(
                id=txn_id,
                date=date_val,
                raw_description=raw_desc,
                amount=final_amount,
                raw_type=raw_type,
                account=account,
            )
        )

    return transactions, warnings
