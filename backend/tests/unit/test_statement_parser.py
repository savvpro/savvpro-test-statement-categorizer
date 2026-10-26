"""Unit tests for CSV statement parser, column mapping, encodings, and file limits."""

from decimal import Decimal
import io
from pathlib import Path
import pytest

from app.services.statement_parser import (
    HEADER_ALIASES,
    StatementParser,
    normalize_header_name,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_normalize_header_name():
    """Verify whitespace, underscores, and casing are normalized in header names."""
    assert normalize_header_name("  Transaction_Date  ") == "transaction date"
    assert normalize_header_name("MONEY_OUT") == "money out"
    assert normalize_header_name("details") == "details"


def test_parse_valid_csv_signed_amount(engine):
    """Test standard valid CSV statement with signed amount column (Format A)."""
    parser = StatementParser(categorizer=engine)
    fixture_path = FIXTURES_DIR / "valid_statement.csv"

    result = parser.parse_file(fixture_path)

    assert result.is_success is True
    assert result.total_rows == 3
    assert result.valid_row_count == 3
    assert result.invalid_row_count == 0
    assert len(result.transactions) == 3

    tx0 = result.transactions[0]
    assert tx0.row_number == 2
    assert tx0.transaction.original_description == "JETBRAINS ALL PRODUCTS PACK"
    assert tx0.transaction.amount == Decimal("-28.90")
    assert tx0.result.category == "Software"


def test_parse_valid_csv_separate_debit_credit_columns(engine):
    """Test standard valid CSV with separate debit and credit columns (Format B)."""
    parser = StatementParser(categorizer=engine)
    fixture_path = FIXTURES_DIR / "separate_columns.csv"

    result = parser.parse_file(fixture_path)

    assert result.is_success is True
    assert result.valid_row_count == 4
    assert result.invalid_row_count == 0

    # Row 2: Debit 15.00 -> amount -15.00
    assert result.transactions[0].transaction.amount == Decimal("-15.00")
    assert result.transactions[0].result.category == "Software"

    # Row 3: Credit 850.00 -> amount 850.00
    assert result.transactions[1].transaction.amount == Decimal("850.00")
    assert result.transactions[1].result.category == "Business Income"

    # Row 4: Debit $12.00 -> amount -12.00
    assert result.transactions[2].transaction.amount == Decimal("-12.00")
    assert result.transactions[2].result.category == "Bank Fees"

    # Row 5: Credit 24.00 -> amount 24.00
    assert result.transactions[3].transaction.amount == Decimal("24.00")
    assert result.transactions[3].result.category == "Refund"


def test_header_aliases_and_casing():
    """Verify parser recognizes diverse column header aliases and mixed casing."""
    csv_data = (
        "POSTED DATE,Narration,Paid Out,Paid In,Currency Code\n"
        "2026-08-01,IDE SUBSCRIPTION,15.00,,USD\n"
        "2026-08-02,CLIENT SETTLEMENT,,1200.00,USD\n"
    )
    parser = StatementParser()
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.is_success is True
    assert result.valid_row_count == 2
    assert result.transactions[0].transaction.amount == Decimal("-15.00")
    assert result.transactions[1].transaction.amount == Decimal("1200.00")


def test_utf8_bom_encoding():
    """Verify UTF-8 with BOM (Byte Order Mark) is parsed cleanly without corrupting the first column."""
    csv_content = (
        "date,description,amount\n"
        "2026-08-01,GITHUB SUBSCRIPTION,-10.00\n"
    )
    raw_bytes = csv_content.encode("utf-8-sig")

    parser = StatementParser()
    result = parser.parse_file(raw_bytes)

    assert result.is_success is True
    assert result.valid_row_count == 1
    assert result.transactions[0].transaction.original_description == "GITHUB SUBSCRIPTION"


def test_cp1252_windows_encoding_fallback():
    """Verify Windows-1252 encoded files (e.g. smart quotes or currency symbols) decode cleanly."""
    # Byte 0x93 and 0x94 are smart quotes in cp1252 that fail standard utf-8 decoding
    cp1252_data = b"date,description,amount\n2026-08-01,CLIENT \x93PAYMENT\x94,500.00\n"

    parser = StatementParser()
    result = parser.parse_file(cp1252_data)

    assert result.is_success is True
    assert result.valid_row_count == 1
    assert "PAYMENT" in result.transactions[0].transaction.original_description


def test_empty_file_handling():
    """Verify empty input returns structured EMPTY_FILE error."""
    parser = StatementParser()
    result = parser.parse_file(b"")

    assert result.is_success is False
    assert len(result.errors) == 1
    assert result.errors[0].error_code == "EMPTY_FILE"


def test_header_only_file():
    """Verify CSV containing only header row returns structured HEADER_ONLY error."""
    csv_data = "date,description,amount\n"
    parser = StatementParser()
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.is_success is False
    assert result.total_rows == 0
    assert any(e.error_code == "HEADER_ONLY" for e in result.errors)


def test_missing_required_columns():
    """Verify missing required columns return MISSING_REQUIRED_COLUMNS error."""
    parser = StatementParser()
    fixture_path = FIXTURES_DIR / "missing_columns.csv"

    result = parser.parse_file(fixture_path)

    assert result.is_success is False
    assert any(e.error_code == "MISSING_REQUIRED_COLUMNS" for e in result.errors)


def test_duplicate_column_headers():
    """Verify duplicate headers in CSV produce DUPLICATE_HEADERS error."""
    csv_data = "date,description,amount,amount\n2026-08-01,Test,10,20\n"
    parser = StatementParser()
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.is_success is False
    assert any(e.error_code == "DUPLICATE_HEADERS" for e in result.errors)


def test_conflicting_amount_columns():
    """Verify specifying both single amount and debit/credit columns raises error."""
    csv_data = "date,description,amount,debit,credit\n2026-08-01,Test,10,10,0\n"
    parser = StatementParser()
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.is_success is False
    assert any(e.error_code == "AMBIGUOUS_AMOUNT_COLUMNS" for e in result.errors)


def test_blank_lines_skipped_safely():
    """Verify blank or whitespace-only rows between valid records are ignored without error."""
    csv_data = (
        "date,description,amount\n"
        "2026-08-01,GITHUB COPILOT,-10.00\n"
        "\n"
        "   \n"
        "2026-08-02,AWS BILLING,-20.00\n"
    )
    parser = StatementParser()
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.is_success is True
    assert result.total_rows == 2
    assert result.valid_row_count == 2
    assert result.invalid_row_count == 0


def test_file_size_limit_enforced():
    """Verify files exceeding max_file_size limit are rejected with FILE_TOO_LARGE."""
    small_limit_parser = StatementParser(max_file_size=50)
    data = b"date,description,amount\n2026-08-01,A VERY LONG DESCRIPTION THAT EXCEEDS FIFTY BYTES,-10.00\n"

    result = small_limit_parser.parse_file(data)

    assert result.is_success is False
    assert any(e.error_code == "FILE_TOO_LARGE" for e in result.errors)


def test_max_data_rows_limit_enforced():
    """Verify parsing stops and reports error when data rows exceed configured maximum."""
    row_limit_parser = StatementParser(max_data_rows=2)
    csv_data = (
        "date,description,amount\n"
        "2026-08-01,ROW 1,-10.00\n"
        "2026-08-02,ROW 2,-20.00\n"
        "2026-08-03,ROW 3 EXCEEDING LIMIT,-30.00\n"
    )
    result = row_limit_parser.parse_file(io.StringIO(csv_data))

    assert result.valid_row_count == 2
    assert any(e.error_code == "TOO_MANY_ROWS" for e in result.errors)
