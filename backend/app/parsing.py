"""
CSV statement parsing, header normalization, monetary decimal conversion,
and validation logic for Freelance Ledger.
"""

import csv
import io
import re
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .categorizer import categorize_transaction, normalize_description
from .models import ParseIssue, Transaction

# Column header recognition mappings (lowercase, trimmed)
HEADER_ALIASES = {
    "date": [
        "date", "transaction date", "posted date", "trans date",
        "post date", "txn date", "effective date", "posting date"
    ],
    "description": [
        "description", "merchant", "details", "transaction",
        "memo", "payee", "name", "narrative", "transaction description"
    ],
    "amount": [
        "amount", "transaction amount", "total", "net amount",
        "value", "sum"
    ],
    "debit": [
        "debit", "withdrawal", "charge", "spent", "debits", "debit amount"
    ],
    "credit": [
        "credit", "deposit", "payment received", "inflow", "credits", "credit amount"
    ],
}


def parse_decimal_amount(val: str) -> Decimal | None:
    """
    Parses a string into a precise Decimal.
    Handles:
    - (123.45) -> -123.45
    - 123.45 DR -> -123.45
    - 123.45 CR -> +123.45
    - -$1,234.56 -> -1234.56
    - $1,234.56- -> -1234.56
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None

    # Check for trailing or leading DR/CR notation
    is_dr = bool(re.search(r"\bDR\b", s, re.IGNORECASE))
    is_cr = bool(re.search(r"\bCR\b", s, re.IGNORECASE))

    # Clean out DR/CR first before stripping whitespace
    s = re.sub(r"(?i)\b(DR|CR)\b", "", s)
    # Clean out currency symbols, commas, spaces
    s = re.sub(r"[$\€\£\¥\s]", "", s)

    # Check for parentheses: (123.45) -> negative
    is_parentheses = False
    if s.startswith("(") and s.endswith(")"):
        is_parentheses = True
        s = s[1:-1].strip()

    # Check for trailing minus: 123.45- -> -123.45
    is_trailing_minus = False
    if s.endswith("-"):
        is_trailing_minus = True
        s = s[:-1].strip()

    # Remove thousands separators
    s = s.replace(",", "")

    try:
        dec = Decimal(s)
        if is_parentheses or is_trailing_minus or is_dr:
            if dec > 0:
                dec = -dec
        elif is_cr and dec < 0:
            dec = -dec
        return dec
    except (InvalidOperation, ValueError):
        return None


def parse_date_string(val: str) -> tuple[str | None, datetime | None]:
    """
    Parses multiple common date formats into ISO YYYY-MM-DD.
    Returns: (iso_date_str, datetime_obj)
    """
    if not val:
        return None, None
    s = val.strip()

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%m/%d/%y",
        "%d/%m/%y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            # Enforce 4-digit reasonable year
            if dt.year < 1990 or dt.year > 2040:
                continue
            return dt.strftime("%Y-%m-%d"), dt
        except ValueError:
            continue

    return None, None


def identify_columns(headers: list[str]) -> dict[str, int]:
    """
    Maps column roles ('date', 'description', 'amount', 'debit', 'credit')
    to their index in the header row.
    """
    mapping: dict[str, int] = {}
    normalized = [h.strip().lower() for h in headers]

    for role, aliases in HEADER_ALIASES.items():
        for idx, h in enumerate(normalized):
            if h in aliases or any(h == alias for alias in aliases):
                mapping[role] = idx
                break

    # If exact alias not matched, try substring matching
    for role, aliases in HEADER_ALIASES.items():
        if role not in mapping:
            for idx, h in enumerate(normalized):
                if any(alias in h for alias in aliases):
                    mapping[role] = idx
                    break

    return mapping


def detect_duplicates(transactions: list[Transaction]) -> None:
    """
    Detects potential duplicate transactions:
    Same normalized description and identical amount within a 3-day window.
    Marks is_duplicate and sets duplicate_reason.
    """
    parsed_items = []
    for tx in transactions:
        dt = datetime.strptime(tx.date, "%Y-%m-%d")
        parsed_items.append((dt, tx))

    # Compare pairs
    for i in range(len(parsed_items)):
        dt_i, tx_i = parsed_items[i]
        for j in range(i + 1, len(parsed_items)):
            dt_j, tx_j = parsed_items[j]

            # If descriptions match and amounts match
            if (
                tx_i.normalized_description == tx_j.normalized_description
                and tx_i.amount == tx_j.amount
                and abs((dt_i - dt_j).days) <= 3
            ):
                tx_i.is_duplicate = True
                tx_j.is_duplicate = True
                reason_msg = (
                    f"Possible duplicate: matched {tx_i.amount} at '{tx_i.description}' "
                    f"within {abs((dt_i - dt_j).days)} day(s)"
                )
                tx_i.duplicate_reason = reason_msg
                tx_j.duplicate_reason = reason_msg


def parse_csv_statement(
    file_content: bytes,
    max_rows: int = 10000
) -> tuple[list[Transaction], list[ParseIssue], int]:
    """
    Parses statement CSV content bytes.
    Returns: (valid_transactions, parse_issues, total_rows_read)
    """
    # Attempt to decode using UTF-8 (handling BOM) or Latin-1
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = file_content.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ValueError("Unable to decode statement file using UTF-8 or standard encodings.")

    f = io.StringIO(text)
    reader = csv.reader(f)

    headers = None
    for row in reader:
        # Skip leading empty rows
        if any(c.strip() for c in row):
            headers = [c.strip() for c in row]
            break

    if not headers:
        raise ValueError("The uploaded CSV file is empty or missing a valid header row.")

    col_map = identify_columns(headers)

    if "date" not in col_map:
        raise ValueError(
            f"Missing required 'Date' column. Found columns: {', '.join(headers)}. "
            f"Expected aliases like 'Date', 'Transaction Date', or 'Posted Date'."
        )

    if "description" not in col_map:
        raise ValueError(
            f"Missing required 'Description' column. Found columns: {', '.join(headers)}. "
            f"Expected aliases like 'Description', 'Merchant', or 'Details'."
        )

    has_amount = "amount" in col_map
    has_debit_credit = "debit" in col_map or "credit" in col_map

    if not has_amount and not has_debit_credit:
        raise ValueError(
            f"Missing required amount column(s). Found columns: {', '.join(headers)}. "
            f"Expected either an 'Amount' column, or separate 'Debit' and 'Credit' columns."
        )

    transactions: list[Transaction] = []
    issues: list[ParseIssue] = []
    row_count = 0

    date_idx = col_map["date"]
    desc_idx = col_map["description"]
    amount_idx = col_map.get("amount")
    debit_idx = col_map.get("debit")
    credit_idx = col_map.get("credit")

    for raw_row in reader:
        # Check row limits
        if row_count >= max_rows:
            issues.append(
                ParseIssue(
                    row_number=row_count + 1,
                    raw_content="",
                    issue=f"Maximum statement row limit of {max_rows} reached. Remaining rows were truncated."
                )
            )
            break

        # Skip empty lines
        if not any(c.strip() for c in raw_row):
            continue

        row_count += 1
        raw_line_str = ",".join(raw_row)

        if len(raw_row) <= max(col_map.values()):
            issues.append(
                ParseIssue(
                    row_number=row_count,
                    raw_content=raw_line_str,
                    issue=f"Row has {len(raw_row)} column(s), expected at least {max(col_map.values()) + 1}."
                )
            )
            continue

        # Extract and parse Date
        raw_date = raw_row[date_idx].strip()
        iso_date, _dt_obj = parse_date_string(raw_date)
        if not iso_date:
            issues.append(
                ParseIssue(
                    row_number=row_count,
                    raw_content=raw_line_str,
                    issue=f"Invalid date format '{raw_date}'. Expected formats: YYYY-MM-DD or MM/DD/YYYY."
                )
            )
            continue

        # Extract Description
        raw_desc = raw_row[desc_idx].strip()
        if not raw_desc:
            issues.append(
                ParseIssue(
                    row_number=row_count,
                    raw_content=raw_line_str,
                    issue="Description field is empty or blank."
                )
            )
            continue

        # Extract Amount
        amount_val: Decimal | None = None
        if has_amount and amount_idx is not None and raw_row[amount_idx].strip():
            amount_val = parse_decimal_amount(raw_row[amount_idx])
        elif has_debit_credit:
            debit_raw = raw_row[debit_idx].strip() if debit_idx is not None and debit_idx < len(raw_row) else ""
            credit_raw = raw_row[credit_idx].strip() if credit_idx is not None and credit_idx < len(raw_row) else ""

            debit_dec = parse_decimal_amount(debit_raw) if debit_raw else None
            credit_dec = parse_decimal_amount(credit_raw) if credit_raw else None

            if debit_dec is not None and debit_dec != Decimal(0):
                # Debit is an expense (negative)
                amount_val = -abs(debit_dec)
            elif credit_dec is not None and credit_dec != Decimal(0):
                # Credit is an inflow (positive)
                amount_val = abs(credit_dec)
            elif debit_raw or credit_raw:
                amount_val = Decimal("0.00")

        if amount_val is None:
            issues.append(
                ParseIssue(
                    row_number=row_count,
                    raw_content=raw_line_str,
                    issue="Unable to parse valid monetary amount from row."
                )
            )
            continue

        # Categorize via deterministic brain
        category, confidence, reason, needs_review, direction = categorize_transaction(
            raw_desc, amount_val
        )

        txn = Transaction(
            id=f"txn_{uuid.uuid4().hex[:10]}",
            date=iso_date,
            original_date=raw_date,
            description=raw_desc,
            normalized_description=normalize_description(raw_desc),
            amount=amount_val,
            direction=direction,
            category=category,
            confidence=confidence,
            reason=reason,
            needs_review=needs_review,
            user_edited=False,
            notes=None,
            is_duplicate=False,
            duplicate_reason=None,
        )
        transactions.append(txn)

    # Run duplicate detection pass
    detect_duplicates(transactions)

    return transactions, issues, row_count
