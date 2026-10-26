"""
CSV parser with validation, encoding safety, ambiguous date detection,
and finite Decimal validation.

Expected CSV columns: Date, Description, Amount
Amount convention: positive = money IN, negative = money OUT.
"""

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Tuple

from backend.models import RawTransaction


REQUIRED_COLUMNS = {"date", "description", "amount"}

# Accepted date formats tried in order
DATE_FORMATS = [
    ("%Y-%m-%d", False),
    ("%m/%d/%Y", True),
    ("%d/%m/%Y", True),
    ("%m-%d-%Y", True),
    ("%d-%m-%Y", True),
]


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace(" ", "_")


def _check_date_ambiguity(raw: str) -> bool:
    """Check if date has parts that could be either month or day (both <= 12)."""
    parts = re.split(r"[-/.]", raw.strip())
    if len(parts) == 3:
        try:
            p1, p2 = int(parts[0]), int(parts[1])
            # If neither is a 4-digit year and both are <= 12 and different
            if 1 <= p1 <= 12 and 1 <= p2 <= 12 and p1 != p2:
                return True
        except ValueError:
            pass
    return False


def _parse_date(raw: str, row_num: int) -> tuple[date, str | None]:
    """
    Try parsing date across multiple formats.
    Returns (parsed_date, optional_ambiguity_warning).
    """
    raw_clean = raw.strip()
    ambiguity_warning = None

    if _check_date_ambiguity(raw_clean):
        ambiguity_warning = (
            f"Row {row_num}: Date '{raw_clean}' is ambiguous between MM/DD and DD/MM. "
            f"Parsed using default MM/DD/YYYY format."
        )

    for fmt, _ in DATE_FORMATS:
        try:
            return datetime.strptime(raw_clean, fmt).date(), ambiguity_warning
        except ValueError:
            continue

    raise ValueError(
        f"Row {row_num}: cannot parse date '{raw_clean}'. "
        f"Accepted formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY."
    )


def _parse_amount(raw: str, row_num: int) -> Decimal:
    """
    Parse a monetary amount to Decimal.
    Validates that the amount is finite (rejects NaN, Infinity, -Infinity).
    """
    cleaned = raw.strip().replace("$", "").replace(",", "")
    try:
        val = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        raise ValueError(
            f"Row {row_num}: '{raw}' is not a valid amount. "
            f"Expected a finite number like 100.00 or -50.25."
        )

    if not val.is_finite() or val.is_nan():
        raise ValueError(
            f"Row {row_num}: '{raw}' is not a finite numerical amount."
        )

    if abs(val) > Decimal("999999999999.99") or val != val.quantize(Decimal("0.01")):
        raise ValueError(f"Row {row_num}: amount must be within 999999999999.99 and have at most two decimal places.")
    return val


def parse_csv(file_content: str | bytes) -> Tuple[list[RawTransaction], list[str]]:
    """
    Parse CSV content into a list of RawTransactions with robust error reporting.

    Returns:
        (transactions, warnings)

    Raises:
        ValueError: if required columns are missing, file is corrupt, or empty.
    """
    warnings: list[str] = []

    # Handle encoding safely
    if isinstance(file_content, bytes):
        try:
            file_content = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                file_content = file_content.decode("latin-1")
                warnings.append("Notice: File was decoded using Latin-1 encoding instead of UTF-8.")
            except Exception as e:
                raise ValueError(f"Unable to decode CSV file. Please upload a UTF-8 encoded CSV. Error: {e}")

    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except csv.Error as e:
        raise ValueError(f"Malformed CSV file structure: {e}")

    if reader.fieldnames is None:
        raise ValueError("The uploaded file is empty or not a valid CSV.")

    # Normalize headers
    headers = [_normalize_header(h) for h in reader.fieldnames if h]
    if len(headers) != len(set(headers)):
        raise ValueError("Duplicate column names are not supported. Use unique Date, Description, and Amount columns.")
    normalized = {_normalize_header(h): h for h in reader.fieldnames if h}
    missing = REQUIRED_COLUMNS - set(normalized.keys())
    if missing:
        raise ValueError(
            f"Missing required column(s): {', '.join(sorted(missing))}. "
            f"The CSV must include Date, Description, and Amount columns."
        )

    transactions: list[RawTransaction] = []

    try:
        for row_num, row in enumerate(reader, start=2):
            if None in row:
                warnings.append(f"Row {row_num}: extra columns; row skipped. Quote descriptions and amounts containing commas.")
                continue
            # Skip completely blank rows
            if all(not v or not v.strip() for v in row.values() if v is not None):
                warnings.append(f"Row {row_num}: empty row skipped.")
                continue

            # Validate individual fields
            date_raw = row.get(normalized.get("date", ""), "")
            desc_raw = row.get(normalized.get("description", ""), "")
            amt_raw = row.get(normalized.get("amount", ""), "")

            date_str = date_raw.strip() if date_raw else ""
            desc_str = desc_raw.strip() if desc_raw else ""
            amt_str = amt_raw.strip() if amt_raw else ""

            if not date_str:
                warnings.append(f"Row {row_num}: 'Date' is empty; row skipped.")
                continue
            if not desc_str:
                warnings.append(f"Row {row_num}: 'Description' is empty; row skipped.")
                continue
            if not amt_str:
                warnings.append(f"Row {row_num}: 'Amount' is empty; row skipped.")
                continue

            try:
                parsed_date, amb_warn = _parse_date(date_str, row_num)
                if amb_warn:
                    warnings.append(amb_warn)
            except ValueError as e:
                warnings.append(str(e))
                continue

            try:
                parsed_amount = _parse_amount(amt_str, row_num)
            except ValueError as e:
                warnings.append(str(e))
                continue

            transactions.append(
                RawTransaction(
                    date=parsed_date,
                    description=desc_str,
                    amount=parsed_amount,
                )
            )
    except csv.Error as e:
        warnings.append(f"Malformed CSV row encountered: {e}")

    if not transactions:
        raise ValueError(
            "No valid transactions found. Check that the CSV has Date, Description, "
            "and Amount columns with at least one parseable row."
        )

    return transactions, warnings
