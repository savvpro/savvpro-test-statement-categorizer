"""
CSV Statement Parser and Validator.

Supports both 3-column (Date, Description, Amount) and 4-column (Date, Description, Debit, Credit)
formats with flexible header aliases, date formats, and currency sanitization.
"""

import csv
import io
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .models import Transaction
from .categorizer import categorize_transaction


MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROW_COUNT = 5000


class CSVValidationError(Exception):
    """Raised when CSV structure, headers, or data validation fails."""
    def __init__(self, message: str, row: Optional[int] = None):
        self.message = message
        self.row = row
        super().__init__(f"Row {row}: {message}" if row else message)


# Header alias mappings (normalized lowercase)
DATE_ALIASES = {"date", "transaction date", "trans date", "posting date", "posted date"}
DESC_ALIASES = {"description", "desc", "payee", "merchant", "details", "memo", "name"}
AMOUNT_ALIASES = {"amount", "trans amount", "transaction amount", "total"}
DEBIT_ALIASES = {"debit", "withdrawal", "outflow", "spent", "charge"}
CREDIT_ALIASES = {"credit", "deposit", "inflow", "received"}


def normalize_header(header: str) -> str:
    """Strip quotes, whitespace, and lowercase the header name."""
    return re.sub(r"[^a-z0-9 ]+", "", header.lower().strip())


def identify_columns(headers: List[str]) -> Tuple[int, int, Optional[int], Optional[int], Optional[int]]:
    """
    Identifies column indices for Date, Description, Amount, Debit, Credit.
    Returns: (date_idx, desc_idx, amount_idx, debit_idx, credit_idx)
    """
    date_idx: Optional[int] = None
    desc_idx: Optional[int] = None
    amount_idx: Optional[int] = None
    debit_idx: Optional[int] = None
    credit_idx: Optional[int] = None

    for idx, raw_h in enumerate(headers):
        h = normalize_header(raw_h)
        if date_idx is None and h in DATE_ALIASES:
            date_idx = idx
        elif desc_idx is None and h in DESC_ALIASES:
            desc_idx = idx
        elif amount_idx is None and h in AMOUNT_ALIASES:
            amount_idx = idx
        elif debit_idx is None and h in DEBIT_ALIASES:
            debit_idx = idx
        elif credit_idx is None and h in CREDIT_ALIASES:
            credit_idx = idx

    if date_idx is None:
        raise CSVValidationError("Missing required Date column (accepted headers: Date, Transaction Date, Posting Date).")
    if desc_idx is None:
        raise CSVValidationError("Missing required Description column (accepted headers: Description, Payee, Merchant, Details, Memo).")

    has_single_amount = amount_idx is not None
    has_split_columns = (debit_idx is not None) or (credit_idx is not None)

    if not has_single_amount and not has_split_columns:
        raise CSVValidationError(
            "Missing Amount column(s). Must include either an 'Amount' column or 'Debit'/'Credit' columns."
        )

    return date_idx, desc_idx, amount_idx, debit_idx, credit_idx


def parse_date(raw_date: str, row_num: int) -> str:
    """
    Validates and standardizes a date string into ISO YYYY-MM-DD.
    Supports formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, YYYY/MM/DD, MM-DD-YYYY.
    """
    raw_date = raw_date.strip()
    if not raw_date:
        raise CSVValidationError("Date field cannot be empty.", row=row_num)

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%Y.%m.%d",
        "%m/%d/%y",
        "%d/%m/%y",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(raw_date, fmt)
            # Basic sanity check on year
            if parsed.year < 1990 or parsed.year > 2040:
                raise CSVValidationError(f"Invalid transaction year: {parsed.year}.", row=row_num)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise CSVValidationError(
        f"Unable to parse date '{raw_date}'. Supported formats: YYYY-MM-DD, MM/DD/YYYY.",
        row=row_num
    )


def clean_currency_string(val: str) -> str:
    """Cleans a monetary string (removes currency symbols, commas, trailing spaces)."""
    val = val.strip()
    # Check for accounting parenthesis format: ($50.00) -> -50.00
    if val.startswith("(") and val.endswith(")"):
        val = "-" + val[1:-1]
    # Remove currency symbols ($ € £ ¥) and thousands separators (,)
    val = re.sub(r"[\$\€\£\¥\,]", "", val).strip()
    return val


def parse_amount(
    row: List[str],
    amount_idx: Optional[int],
    debit_idx: Optional[int],
    credit_idx: Optional[int],
    row_num: int
) -> float:
    """
    Extracts and standardizes the monetary amount as float.
    Expenses/debits are negative (< 0), deposits/credits/inflows are positive (> 0).
    """
    # 1. Debit / Credit split columns
    if debit_idx is not None or credit_idx is not None:
        raw_debit = row[debit_idx].strip() if debit_idx is not None and debit_idx < len(row) else ""
        raw_credit = row[credit_idx].strip() if credit_idx is not None and credit_idx < len(row) else ""

        raw_debit_clean = clean_currency_string(raw_debit)
        raw_credit_clean = clean_currency_string(raw_credit)

        has_debit = bool(raw_debit_clean and raw_debit_clean not in ["0", "0.00", "-"])
        has_credit = bool(raw_credit_clean and raw_credit_clean not in ["0", "0.00", "-"])

        if has_debit and has_credit:
            # Both populated: compute net
            try:
                debit_val = abs(float(raw_debit_clean))
                credit_val = abs(float(raw_credit_clean))
                return round(credit_val - debit_val, 2)
            except ValueError:
                raise CSVValidationError(f"Invalid debit/credit numbers: '{raw_debit}', '{raw_credit}'.", row=row_num)

        if has_debit:
            try:
                val = abs(float(raw_debit_clean))
                return round(-val, 2)
            except ValueError:
                raise CSVValidationError(f"Invalid debit amount: '{raw_debit}'.", row=row_num)

        if has_credit:
            try:
                val = abs(float(raw_credit_clean))
                return round(val, 2)
            except ValueError:
                raise CSVValidationError(f"Invalid credit amount: '{raw_credit}'.", row=row_num)

        # If both are empty and no amount column exists
        if amount_idx is None:
            raise CSVValidationError("Both Debit and Credit columns are empty.", row=row_num)

    # 2. Single Amount column
    if amount_idx is not None:
        if amount_idx >= len(row):
            raise CSVValidationError("Row missing Amount column value.", row=row_num)
        raw_amount = row[amount_idx].strip()
        if not raw_amount:
            raise CSVValidationError("Amount field cannot be empty.", row=row_num)

        clean_amt = clean_currency_string(raw_amount)
        try:
            return round(float(clean_amt), 2)
        except ValueError:
            raise CSVValidationError(f"Invalid amount value: '{raw_amount}'.", row=row_num)

    raise CSVValidationError("Could not determine transaction amount.", row=row_num)


def parse_csv_content(content: bytes) -> Tuple[List[Transaction], List[str]]:
    """
    Parses CSV bytes safely, validates all rows, categorizes each transaction,
    and returns a tuple of (transactions, warnings).
    """
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise CSVValidationError(f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.")

    if not content or content.strip() == b"":
        raise CSVValidationError("Uploaded CSV file is empty.")

    # Decode bytes with UTF-8 (handling BOM if present) or fallback to latin-1
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except UnicodeDecodeError:
            raise CSVValidationError("Failed to decode file. Please ensure it is saved in UTF-8 or ASCII encoding.")

    # Parse CSV stream safely
    stream = io.StringIO(text.strip())
    reader = csv.reader(stream)

    try:
        headers = next(reader)
    except StopIteration:
        raise CSVValidationError("CSV file contains no data or headers.")

    if not headers or all(not h.strip() for h in headers):
        raise CSVValidationError("CSV file header row is empty.")

    date_idx, desc_idx, amount_idx, debit_idx, credit_idx = identify_columns(headers)

    transactions: List[Transaction] = []
    warnings: List[str] = []
    row_count = 0

    for row_idx, row in enumerate(reader, start=2):
        # Skip completely empty rows
        if not row or all(not cell.strip() for cell in row):
            continue

        row_count += 1
        if row_count > MAX_ROW_COUNT:
            raise CSVValidationError(f"File exceeds maximum allowed rows ({MAX_ROW_COUNT}).")

        # Validate Date
        if date_idx >= len(row):
            raise CSVValidationError("Row has fewer columns than required (missing Date).", row=row_idx)
        std_date = parse_date(row[date_idx], row_idx)

        # Validate Description
        raw_desc = row[desc_idx].strip() if desc_idx < len(row) else ""
        if not raw_desc:
            warnings.append(f"Row {row_idx}: Empty description; flagged for Needs Review.")

        # Validate Amount
        amount = parse_amount(row, amount_idx, debit_idx, credit_idx, row_idx)

        # Run Categorization Brain
        decision = categorize_transaction(raw_desc, amount)

        # Generate unique ID (preserving duplicates with distinct IDs)
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"

        tx = Transaction(
            id=tx_id,
            date=std_date,
            description=raw_desc if raw_desc else "[No description provided]",
            amount=amount,
            category=decision.category,
            confidence=decision.confidence,
            status=decision.status,
            matched_rule=decision.matched_rule,
            is_reviewed=False
        )
        transactions.append(tx)

    if not transactions:
        raise CSVValidationError("CSV contains headers but no valid transaction rows.")

    return transactions, warnings
