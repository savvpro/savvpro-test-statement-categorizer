"""CSV Statement Parser and Import Pipeline Service.

Parses bank and credit card statement CSVs, handles column mapping,
validates dates and monetary precision, isolates row-level errors,
detects potential duplicates, and integrates with the Phase 1 categorization engine.
"""

import csv
import datetime
from decimal import Decimal, InvalidOperation
import io
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.schemas.import_result import (
    CategorizedTransaction,
    ImportResult,
    ImportWarning,
    RowError,
)
from app.schemas.transaction import TransactionInput
from app.services.categorizer import CategorizationEngine
from app.services.duplicate_detector import DuplicateDetector


# Configurable defaults
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
DEFAULT_MAX_DATA_ROWS = 10_000

# Canonical header mappings
HEADER_ALIASES: Dict[str, List[str]] = {
    "date": [
        "date",
        "transaction_date",
        "transaction date",
        "posted_date",
        "posted date",
        "post_date",
        "post date",
        "trans_date",
        "trans date",
        "booking_date",
        "booking date",
    ],
    "description": [
        "description",
        "details",
        "narration",
        "merchant",
        "transaction_description",
        "transaction description",
        "memo",
        "payee",
        "name",
    ],
    "amount": [
        "amount",
        "transaction_amount",
        "transaction amount",
        "value",
        "total",
    ],
    "debit": [
        "debit",
        "withdrawal",
        "money_out",
        "money out",
        "debit_amount",
        "debit amount",
        "paid_out",
        "paid out",
    ],
    "credit": [
        "credit",
        "deposit",
        "money_in",
        "money in",
        "credit_amount",
        "credit amount",
        "paid_in",
        "paid in",
    ],
    "currency": [
        "currency",
        "currency_code",
        "currency code",
        "curr",
    ],
}

# Currency symbol mapping
CURRENCY_SYMBOLS: Dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "C$": "CAD",
    "A$": "AUD",
}


class DateParsingError(Exception):
    """Custom exception raised during date parsing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MonetaryParsingError(Exception):
    """Custom exception raised during amount parsing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_header_name(header: str) -> str:
    """Normalize a CSV column header name for alias lookup."""
    cleaned = header.strip().lstrip("\ufeff").lower()
    # Normalize multiple whitespace or underscores
    cleaned = re.sub(r"[\s_]+", " ", cleaned)
    return cleaned


def parse_monetary_amount(raw_val: Any) -> Tuple[Decimal, Optional[str]]:
    """Parse a monetary value into Decimal and detect embedded currency symbol if present.

    Handles:
    - Standard positive/negative numbers: '125.50', '-45.25'
    - Thousands separators: '1,250.00', '-10,500.50'
    - Currency symbols: '$125.50', '€45.00'
    - Accounting negative format: '(45.25)' -> -45.25

    Rejects:
    - Malformed strings ('abc', '12.34.56')
    - Improper thousands grouping ('1,25,0.00', '1,2.00')
    - NaN and Infinity
    """
    if raw_val is None:
        raise MonetaryParsingError("INVALID_AMOUNT", "Amount cell is null or empty.")

    s = str(raw_val).strip()
    if not s:
        raise MonetaryParsingError("INVALID_AMOUNT", "Amount cell is empty.")

    detected_currency: Optional[str] = None

    # Check for accounting-style parentheses: (123.45) -> -123.45
    is_accounting_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_accounting_negative = True
        s = s[1:-1].strip()

    # Detect and strip currency symbols
    for sym, curr_code in CURRENCY_SYMBOLS.items():
        if s.startswith(sym):
            detected_currency = curr_code
            s = s[len(sym) :].strip()
            break
        elif s.endswith(sym):
            detected_currency = curr_code
            s = s[: -len(sym)].strip()
            break

    # If starts with negative sign after currency symbol, handle cleanly
    is_standard_negative = False
    if s.startswith("-"):
        is_standard_negative = True
        s = s[1:].strip()
    elif s.startswith("+"):
        s = s[1:].strip()

    if is_accounting_negative and is_standard_negative:
        raise MonetaryParsingError("INVALID_AMOUNT", f"Conflicting negative signs in amount: '{raw_val}'")

    # Validate numeric format and proper comma grouping (e.g. 1,234.56, but reject 1,23,45.6 or 1,2.5)
    # Allows plain digits: ^\d+(\.\d+)?$ OR valid comma separated: ^\d{1,3}(,\d{3})+(\.\d+)?$
    plain_pattern = re.compile(r"^\d+(\.\d+)?$")
    comma_pattern = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")

    if not (plain_pattern.match(s) or comma_pattern.match(s)):
        raise MonetaryParsingError(
            "INVALID_AMOUNT", f"Malformed monetary amount format or invalid thousands grouping: '{raw_val}'"
        )

    # Remove valid thousands commas
    clean_numeric_str = s.replace(",", "")

    try:
        dec = Decimal(clean_numeric_str)
    except (InvalidOperation, TypeError) as exc:
        raise MonetaryParsingError("INVALID_AMOUNT", f"Cannot convert amount to Decimal: '{raw_val}'") from exc

    if dec.is_nan() or dec.is_infinite():
        raise MonetaryParsingError("INVALID_AMOUNT", f"Monetary amount must be finite, received: {raw_val}")

    if is_accounting_negative or is_standard_negative:
        dec = -dec

    return dec, detected_currency


def parse_date(
    val: str,
    day_first: Optional[bool] = None,
    date_format: Optional[str] = None,
) -> datetime.date:
    """Parse a date string into a datetime.date object.

    Handles ISO formats (YYYY-MM-DD, YYYY/MM/DD), unambiguous DD/MM/YYYY and MM/DD/YYYY,
    and explicitly configured date formats. Rejects ambiguous dates unless day_first
    or date_format is specified.
    """
    if not val or not val.strip():
        raise DateParsingError("INVALID_DATE", "Date field is empty.")

    s = val.strip()

    # Explicit format provided
    if date_format:
        try:
            return datetime.datetime.strptime(s, date_format).date()
        except ValueError as exc:
            raise DateParsingError(
                "INVALID_DATE", f"Date '{s}' does not match configured format '{date_format}'."
            ) from exc

    # ISO formats: YYYY-MM-DD or YYYY/MM/DD
    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if iso_match:
        year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        try:
            return datetime.date(year, month, day)
        except ValueError as exc:
            raise DateParsingError("INVALID_DATE", f"Invalid calendar date '{s}': {exc}") from exc

    # Slashed or hyphenated: DD/MM/YYYY or MM/DD/YYYY
    slash_match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if slash_match:
        part1, part2, year = int(slash_match.group(1)), int(slash_match.group(2)), int(slash_match.group(3))

        # Check bounds
        if part1 > 31 or part2 > 31 or part1 == 0 or part2 == 0:
            raise DateParsingError("INVALID_DATE", f"Date values out of calendar range: '{s}'")

        # If part1 > 12, it must be day -> DD/MM/YYYY
        if part1 > 12 and part2 <= 12:
            day, month = part1, part2
        # If part2 > 12, it must be day -> MM/DD/YYYY
        elif part2 > 12 and part1 <= 12:
            month, day = part1, part2
        # If both are <= 12 and part1 == part2 (e.g. 05/05/2026), unambiguous
        elif part1 == part2:
            month, day = part1, part2
        else:
            # Ambiguous: e.g. 03/04/2026 (March 4th vs April 3rd)
            if day_first is True:
                day, month = part1, part2
            elif day_first is False:
                month, day = part1, part2
            else:
                raise DateParsingError(
                    "AMBIGUOUS_DATE",
                    f"Date '{s}' is ambiguous between DD/MM/YYYY and MM/DD/YYYY. "
                    "Configure 'day_first' (True/False) or explicit 'date_format'.",
                )

        try:
            return datetime.date(year, month, day)
        except ValueError as exc:
            raise DateParsingError("INVALID_DATE", f"Invalid calendar date '{s}': {exc}") from exc

    raise DateParsingError("INVALID_DATE", f"Unrecognized date format: '{s}'")


class StatementParser:
    """Parser and validation service for bank and credit card CSV statements."""

    def __init__(
        self,
        categorizer: Optional[CategorizationEngine] = None,
        duplicate_detector: Optional[DuplicateDetector] = None,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        max_data_rows: int = DEFAULT_MAX_DATA_ROWS,
        day_first: Optional[bool] = None,
        date_format: Optional[str] = None,
        default_currency: str = "USD",
    ) -> None:
        self.categorizer = categorizer or CategorizationEngine()
        self.duplicate_detector = duplicate_detector or DuplicateDetector()
        self.max_file_size = max_file_size
        self.max_data_rows = max_data_rows
        self.day_first = day_first
        self.date_format = date_format
        self.default_currency = default_currency

    def parse_file(
        self,
        file_input: Union[str, Path, bytes, io.IOBase],
        filename: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> ImportResult:
        """Parse, validate, duplicate-check, and categorize transactions from CSV.

        Args:
            file_input: File path, raw bytes, or file-like buffer.
            filename: Optional source filename for reporting.
            encoding: Optional character encoding (auto-detects UTF-8, UTF-8-BOM, cp1252 if None).

        Returns:
            Structured ImportResult containing categorized transactions, errors, and warnings.
        """
        # Resolve filename if path was given
        if isinstance(file_input, (str, Path)):
            resolved_path = Path(file_input)
            if filename is None:
                filename = resolved_path.name

            # Check file existence and size limit
            if not resolved_path.exists():
                return ImportResult(
                    filename=filename,
                    errors=[
                        RowError(
                            row_number=0,
                            error_code="FILE_NOT_FOUND",
                            message=f"File not found: '{resolved_path}'",
                        )
                    ],
                )

            file_size = resolved_path.stat().st_size
            if file_size > self.max_file_size:
                return ImportResult(
                    filename=filename,
                    errors=[
                        RowError(
                            row_number=0,
                            error_code="FILE_TOO_LARGE",
                            message=(
                                f"File size ({file_size} bytes) exceeds configured "
                                f"limit of {self.max_file_size} bytes."
                            ),
                        )
                    ],
                )

            with open(resolved_path, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(file_input, bytes):
            raw_bytes = file_input
            if len(raw_bytes) > self.max_file_size:
                return ImportResult(
                    filename=filename,
                    errors=[
                        RowError(
                            row_number=0,
                            error_code="FILE_TOO_LARGE",
                            message=(
                                f"File content ({len(raw_bytes)} bytes) exceeds configured "
                                f"limit of {self.max_file_size} bytes."
                            ),
                        )
                    ],
                )
        elif isinstance(file_input, (io.StringIO, io.TextIOBase)):
            text_content = file_input.read()
            raw_bytes = text_content.encode("utf-8")
            if len(raw_bytes) > self.max_file_size:
                return ImportResult(
                    filename=filename,
                    errors=[
                        RowError(
                            row_number=0,
                            error_code="FILE_TOO_LARGE",
                            message=f"File content exceeds limit of {self.max_file_size} bytes.",
                        )
                    ],
                )
        elif isinstance(file_input, (io.BytesIO, io.BufferedIOBase)):
            raw_bytes = file_input.read()
            if len(raw_bytes) > self.max_file_size:
                return ImportResult(
                    filename=filename,
                    errors=[
                        RowError(
                            row_number=0,
                            error_code="FILE_TOO_LARGE",
                            message=f"File content exceeds limit of {self.max_file_size} bytes.",
                        )
                    ],
                )
        else:
            return ImportResult(
                filename=filename,
                errors=[
                    RowError(
                        row_number=0,
                        error_code="INVALID_INPUT_TYPE",
                        message=f"Unsupported file input type: {type(file_input).__name__}",
                    )
                ],
            )

        # Empty file check
        if not raw_bytes or not raw_bytes.strip():
            return ImportResult(
                filename=filename,
                errors=[
                    RowError(
                        row_number=0,
                        error_code="EMPTY_FILE",
                        message="Statement file is empty.",
                    )
                ],
            )

        # Decode content with fallback
        decoded_text, decode_err = self._decode_bytes(raw_bytes, encoding)
        if decode_err:
            return ImportResult(
                filename=filename,
                errors=[
                    RowError(
                        row_number=0,
                        error_code="UNSUPPORTED_ENCODING",
                        message=decode_err,
                    )
                ],
            )

        return self._process_csv_text(decoded_text, filename=filename)

    def _decode_bytes(
        self, raw_bytes: bytes, explicit_encoding: Optional[str]
    ) -> Tuple[str, Optional[str]]:
        """Decode raw bytes using explicit or fallback encodings (utf-8-sig, utf-8, cp1252, latin-1)."""
        encodings_to_try = [explicit_encoding] if explicit_encoding else ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

        for enc in encodings_to_try:
            if not enc:
                continue
            try:
                return raw_bytes.decode(enc), None
            except (UnicodeDecodeError, LookupError):
                continue

        return "", f"Failed to decode file using supported encodings: {encodings_to_try}"

    def _process_csv_text(self, text: str, filename: Optional[str]) -> ImportResult:
        """Parse decoded CSV text, map headers, extract rows, and run categorization pipeline."""
        reader = csv.reader(io.StringIO(text))

        # 1. Read and validate header
        header_row: Optional[List[str]] = None
        header_line_number = 0

        for line_idx, row in enumerate(reader, start=1):
            # Skip empty lines preceding header
            if not row or not any(cell.strip() for cell in row):
                continue
            header_row = row
            header_line_number = line_idx
            break

        if header_row is None:
            return ImportResult(
                filename=filename,
                errors=[
                    RowError(
                        row_number=0,
                        error_code="EMPTY_FILE",
                        message="CSV contains no rows or data.",
                    )
                ],
            )

        # Validate header columns and map them
        mapping, header_errors = self._map_columns(header_row, header_line_number)
        if header_errors:
            return ImportResult(
                filename=filename,
                errors=header_errors,
            )

        # 2. Iterate data rows
        parsed_transactions: List[Tuple[int, TransactionInput]] = []
        row_errors: List[RowError] = []
        total_data_rows = 0

        current_line_num = header_line_number

        for row in reader:
            current_line_num += 1

            # Skip completely blank lines
            if not row or not any(cell.strip() for cell in row):
                continue

            total_data_rows += 1

            # Enforce max data rows limit
            if total_data_rows > self.max_data_rows:
                row_errors.append(
                    RowError(
                        row_number=current_line_num,
                        error_code="TOO_MANY_ROWS",
                        message=(
                            f"Total data row count exceeds maximum configured limit of {self.max_data_rows} rows."
                        ),
                    )
                )
                break

            # Parse row
            tx, err = self._parse_single_row(row, current_line_num, mapping)
            if err:
                row_errors.append(err)
            elif tx:
                parsed_transactions.append((current_line_num, tx))

        # Check if header-only
        if total_data_rows == 0:
            return ImportResult(
                filename=filename,
                total_rows=0,
                errors=[
                    RowError(
                        row_number=header_line_number,
                        error_code="HEADER_ONLY",
                        message="Statement contains header but no transaction data rows.",
                    )
                ],
            )

        # 3. Duplicate Detection on successfully parsed transactions
        duplicate_row_nums, duplicate_warnings = self.duplicate_detector.find_duplicates(parsed_transactions)

        # 4. Run through Phase 1 Categorization Engine
        categorized_items: List[CategorizedTransaction] = []
        for row_num, tx in parsed_transactions:
            cat_result = self.categorizer.categorize(tx)
            is_dup = row_num in duplicate_row_nums
            categorized_items.append(
                CategorizedTransaction(
                    row_number=row_num,
                    transaction=tx,
                    result=cat_result,
                    is_potential_duplicate=is_dup,
                )
            )

        return ImportResult(
            filename=filename,
            total_rows=total_data_rows,
            valid_row_count=len(parsed_transactions),
            categorized_count=len(categorized_items),
            invalid_row_count=len(row_errors),
            duplicate_count=len(duplicate_row_nums),
            transactions=categorized_items,
            errors=row_errors,
            warnings=duplicate_warnings,
        )

    def _map_columns(
        self, header: List[str], header_row_num: int
    ) -> Tuple[Dict[str, int], List[RowError]]:
        """Map CSV column indices to canonical field names and validate presence and uniqueness."""
        mapping: Dict[str, int] = {}
        errors: List[RowError] = []

        seen_headers: Set[str] = set()

        for idx, col in enumerate(header):
            norm_col = normalize_header_name(col)
            if not norm_col:
                continue

            if norm_col in seen_headers:
                errors.append(
                    RowError(
                        row_number=header_row_num,
                        error_code="DUPLICATE_HEADERS",
                        message=f"Duplicate column header found: '{col}'",
                        field_name=norm_col,
                    )
                )
            seen_headers.add(norm_col)

            # Match against known aliases
            matched_canonical: Optional[str] = None
            for canonical, aliases in HEADER_ALIASES.items():
                if norm_col in aliases:
                    matched_canonical = canonical
                    break

            if matched_canonical:
                if matched_canonical in mapping:
                    errors.append(
                        RowError(
                            row_number=header_row_num,
                            error_code="CONFLICTING_COLUMNS",
                            message=(
                                f"Multiple columns map to canonical field '{matched_canonical}': "
                                f"column {mapping[matched_canonical] + 1} and column {idx + 1} ('{col}')"
                            ),
                            field_name=matched_canonical,
                        )
                    )
                else:
                    mapping[matched_canonical] = idx

        if errors:
            return {}, errors

        # Validate required columns
        missing_required: List[str] = []
        if "date" not in mapping:
            missing_required.append("date")
        if "description" not in mapping:
            missing_required.append("description")

        # Amount format: Either 'amount' (Format A) OR ('debit' and 'credit') (Format B)
        has_amount = "amount" in mapping
        has_separate = ("debit" in mapping) and ("credit" in mapping)

        if not has_amount and not has_separate:
            if "debit" in mapping and "credit" not in mapping:
                missing_required.append("credit")
            elif "credit" in mapping and "debit" not in mapping:
                missing_required.append("debit")
            else:
                missing_required.append("amount (or debit and credit)")

        if has_amount and (has_separate or "debit" in mapping or "credit" in mapping):
            errors.append(
                RowError(
                    row_number=header_row_num,
                    error_code="AMBIGUOUS_AMOUNT_COLUMNS",
                    message="CSV contains both single 'amount' column and separate 'debit'/'credit' columns.",
                )
            )
            return {}, errors

        if missing_required:
            errors.append(
                RowError(
                    row_number=header_row_num,
                    error_code="MISSING_REQUIRED_COLUMNS",
                    message=f"Missing required statement column(s): {', '.join(missing_required)}",
                )
            )
            return {}, errors

        return mapping, []

    def _parse_single_row(
        self, row: List[str], row_num: int, mapping: Dict[str, int]
    ) -> Tuple[Optional[TransactionInput], Optional[RowError]]:
        """Parse and validate one CSV row into a TransactionInput object."""
        # 1. Date
        date_idx = mapping["date"]
        if date_idx >= len(row):
            return None, RowError(
                row_number=row_num,
                error_code="MISSING_FIELD",
                field_name="date",
                message=f"Row has {len(row)} columns, expected at least {date_idx + 1} for date.",
            )

        raw_date_str = row[date_idx].strip()
        try:
            parsed_date = parse_date(
                raw_date_str, day_first=self.day_first, date_format=self.date_format
            )
        except DateParsingError as d_err:
            return None, RowError(
                row_number=row_num,
                error_code=d_err.code,
                field_name="date",
                message=d_err.message,
                raw_data=raw_date_str,
            )

        # 2. Description
        desc_idx = mapping["description"]
        if desc_idx >= len(row):
            return None, RowError(
                row_number=row_num,
                error_code="MISSING_FIELD",
                field_name="description",
                message=f"Row has {len(row)} columns, expected at least {desc_idx + 1} for description.",
            )

        raw_desc = row[desc_idx]
        if not raw_desc or not raw_desc.strip():
            return None, RowError(
                row_number=row_num,
                error_code="MISSING_DESCRIPTION",
                field_name="description",
                message="Transaction description is empty or whitespace-only.",
                raw_data=raw_desc,
            )

        # 3. Currency
        currency_val = self.default_currency
        if "currency" in mapping:
            curr_idx = mapping["currency"]
            if curr_idx < len(row) and row[curr_idx].strip():
                currency_val = row[curr_idx].strip().upper()

        # 4. Amount parsing (Format A vs Format B)
        final_amount: Decimal
        embedded_currency: Optional[str] = None

        if "amount" in mapping:
            amt_idx = mapping["amount"]
            if amt_idx >= len(row):
                return None, RowError(
                    row_number=row_num,
                    error_code="MISSING_FIELD",
                    field_name="amount",
                    message=f"Row has {len(row)} columns, expected at least {amt_idx + 1} for amount.",
                )
            raw_amt = row[amt_idx].strip()
            try:
                final_amount, embedded_currency = parse_monetary_amount(raw_amt)
            except MonetaryParsingError as m_err:
                return None, RowError(
                    row_number=row_num,
                    error_code=m_err.code,
                    field_name="amount",
                    message=m_err.message,
                    raw_data=raw_amt,
                )
        else:
            # Format B: Separate debit and credit
            debit_idx = mapping["debit"]
            credit_idx = mapping["credit"]

            raw_debit = row[debit_idx].strip() if debit_idx < len(row) else ""
            raw_credit = row[credit_idx].strip() if credit_idx < len(row) else ""

            debit_amt: Optional[Decimal] = None
            credit_amt: Optional[Decimal] = None

            if raw_debit:
                try:
                    d_val, curr_d = parse_monetary_amount(raw_debit)
                    # Debit is outgoing money; positive debit value represents outflow
                    # If already negative, preserve sign, else negate
                    debit_amt = -abs(d_val)
                    if curr_d:
                        embedded_currency = curr_d
                except MonetaryParsingError as m_err:
                    return None, RowError(
                        row_number=row_num,
                        error_code=m_err.code,
                        field_name="debit",
                        message=f"Invalid debit value: {m_err.message}",
                        raw_data=raw_debit,
                    )

            if raw_credit:
                try:
                    c_val, curr_c = parse_monetary_amount(raw_credit)
                    # Credit is incoming money; positive represents inflow
                    credit_amt = abs(c_val)
                    if curr_c:
                        embedded_currency = curr_c
                except MonetaryParsingError as m_err:
                    return None, RowError(
                        row_number=row_num,
                        error_code=m_err.code,
                        field_name="credit",
                        message=f"Invalid credit value: {m_err.message}",
                        raw_data=raw_credit,
                    )

            # Evaluate debit and credit combination
            has_debit = debit_amt is not None and debit_amt != Decimal("0")
            has_credit = credit_amt is not None and credit_amt != Decimal("0")

            if has_debit and has_credit:
                return None, RowError(
                    row_number=row_num,
                    error_code="BOTH_DEBIT_AND_CREDIT",
                    message=f"Row has both nonzero debit ({raw_debit}) and credit ({raw_credit}).",
                    raw_data=f"debit={raw_debit}, credit={raw_credit}",
                )

            if has_debit:
                final_amount = debit_amt  # type: ignore
            elif has_credit:
                final_amount = credit_amt  # type: ignore
            elif debit_amt == Decimal("0") or credit_amt == Decimal("0"):
                final_amount = Decimal("0")
            else:
                return None, RowError(
                    row_number=row_num,
                    error_code="INVALID_AMOUNT",
                    message="Both debit and credit columns are empty or unspecified.",
                )

        # Use detected currency if row didn't explicitly have currency column
        if embedded_currency and "currency" not in mapping:
            currency_val = embedded_currency

        # Instantiate TransactionInput (reusing Phase 1 model)
        try:
            tx = TransactionInput(
                date=parsed_date,
                original_description=raw_desc,
                amount=final_amount,
                currency=currency_val,
            )
            return tx, None
        except Exception as exc:
            return None, RowError(
                row_number=row_num,
                error_code="VALIDATION_ERROR",
                message=f"Transaction validation failed: {exc}",
            )
