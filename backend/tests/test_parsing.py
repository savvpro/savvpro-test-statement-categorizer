"""
Unit tests for CSV statement parsing, header normalization, and edge case formats.
"""

from decimal import Decimal

import pytest
from app.models import Transaction
from app.parsing import (
    detect_duplicates,
    identify_columns,
    parse_csv_statement,
    parse_date_string,
    parse_decimal_amount,
)


def test_parse_decimal_amount_formats():
    assert parse_decimal_amount("-59.99") == Decimal("-59.99")
    assert parse_decimal_amount("1250.00") == Decimal("1250.00")
    # Currency signs and commas
    assert parse_decimal_amount("-$1,234.56") == Decimal("-1234.56")
    assert parse_decimal_amount("$1,234.56") == Decimal("1234.56")
    # Parentheses notation for negative
    assert parse_decimal_amount("(150.25)") == Decimal("-150.25")
    assert parse_decimal_amount("($150.25)") == Decimal("-150.25")
    # Trailing minus
    assert parse_decimal_amount("85.00-") == Decimal("-85.00")
    # DR / CR notation
    assert parse_decimal_amount("45.00 DR") == Decimal("-45.00")
    assert parse_decimal_amount("500.00 CR") == Decimal("500.00")


def test_parse_date_formats():
    iso, dt = parse_date_string("2026-01-15")
    assert iso == "2026-01-15"
    assert dt is not None and dt.year == 2026

    iso, _dt = parse_date_string("01/15/2026")
    assert iso == "2026-01-15"

    iso, _dt = parse_date_string("15/01/2026")
    assert iso == "2026-01-15"

    iso, _dt = parse_date_string("Jan 15, 2026")
    assert iso == "2026-01-15"


def test_header_column_aliases():
    headers = ["Posting Date", "Transaction Details", "Total Amount"]
    col_map = identify_columns(headers)
    assert col_map["date"] == 0
    assert col_map["description"] == 1
    assert col_map["amount"] == 2


def test_debit_credit_column_recognition():
    headers = ["Date", "Merchant Name", "Debit", "Credit"]
    col_map = identify_columns(headers)
    assert col_map["date"] == 0
    assert col_map["description"] == 1
    assert col_map["debit"] == 2
    assert col_map["credit"] == 3


def test_parse_csv_statement_format_a():
    csv_data = b"""Date,Description,Amount
2026-01-03,ADOBE CREATIVE CLOUD,-59.99
2026-01-04,CLIENT PAYMENT,1250.00
"""
    txns, issues, total_rows = parse_csv_statement(csv_data)
    assert len(txns) == 2
    assert len(issues) == 0
    assert total_rows == 2
    assert txns[0].category == "Software"
    assert txns[0].amount == Decimal("-59.99")
    assert txns[1].category == "Income"
    assert txns[1].amount == Decimal("1250.00")


def test_parse_csv_statement_format_b_debit_credit():
    csv_data = b"""Date,Description,Debit,Credit
2026-01-03,ADOBE CREATIVE CLOUD,59.99,
2026-01-04,CLIENT PAYMENT,,1250.00
"""
    txns, _issues, _total_rows = parse_csv_statement(csv_data)
    assert len(txns) == 2
    assert txns[0].amount == Decimal("-59.99")
    assert txns[1].amount == Decimal("1250.00")


def test_parse_csv_quoted_fields_with_commas():
    csv_data = b"""Date,Description,Amount
2026-01-10,"OFFICE DEPOT, STORE #104, SUPPLIES",-68.50
"""
    txns, _issues, _ = parse_csv_statement(csv_data)
    assert len(txns) == 1
    assert txns[0].description == "OFFICE DEPOT, STORE #104, SUPPLIES"
    assert txns[0].amount == Decimal("-68.50")


def test_parse_csv_utf8_bom():
    csv_data = b"\xef\xbb\xbfDate,Description,Amount\n2026-01-03,GITHUB PRO,-10.00\n"
    txns, _issues, _ = parse_csv_statement(csv_data)
    assert len(txns) == 1
    assert txns[0].category == "Software"


def test_parse_csv_missing_required_headers():
    csv_data = b"""RandomCol1,RandomCol2\nVal1,Val2\n"""
    with pytest.raises(ValueError, match="Missing required"):
        parse_csv_statement(csv_data)


def test_parse_csv_malformed_rows_logged_as_issues():
    csv_data = b"""Date,Description,Amount
2026-01-03,VALID ROW,-20.00
invalid-date,ROW WITH BAD DATE,-30.00
2026-01-05,, -40.00
2026-01-06,BAD AMOUNT,not-a-number
2026-01-07,ANOTHER VALID ROW,-50.00
"""
    txns, issues, total_rows = parse_csv_statement(csv_data)
    assert len(txns) == 2
    assert len(issues) == 3
    assert total_rows == 5


def test_duplicate_charge_detection():
    tx1 = Transaction(
        id="1",
        date="2026-02-10",
        original_date="2026-02-10",
        description="FIGMA MONTHLY SUB",
        normalized_description="FIGMA MONTHLY SUB",
        amount=Decimal("-15.00"),
        direction="expense",
        category="Software",
        confidence=0.98,
        reason="Matched Figma",
    )
    tx2 = Transaction(
        id="2",
        date="2026-02-11",
        original_date="2026-02-11",
        description="FIGMA MONTHLY SUB",
        normalized_description="FIGMA MONTHLY SUB",
        amount=Decimal("-15.00"),
        direction="expense",
        category="Software",
        confidence=0.98,
        reason="Matched Figma",
    )
    detect_duplicates([tx1, tx2])
    assert tx1.is_duplicate is True
    assert tx2.is_duplicate is True
    assert "Possible duplicate" in tx1.duplicate_reason
