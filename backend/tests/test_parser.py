"""
Unit tests for multi-format CSV statement parser.
"""

from pathlib import Path
import pytest
from app.services.parser import parse_csv

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def test_parse_sample_statement_csv():
    file_path = SAMPLE_DIR / "sample_statement.csv"
    assert file_path.exists(), "Sample statement file missing"
    content = file_path.read_bytes()

    txs, warnings = parse_csv(content, "sample_statement.csv")
    assert len(txs) == 33
    assert len(warnings) == 0

    first = txs[0]
    assert first.id == "TXN-001"
    assert first.date == "2024-10-01"
    assert first.raw_description == "GITHUB INC"
    assert first.amount == -25.0


def test_parse_sample_statement_split_csv():
    file_path = SAMPLE_DIR / "sample_statement_split.csv"
    assert file_path.exists(), "Split sample statement file missing"
    content = file_path.read_bytes()

    txs, warnings = parse_csv(content, "sample_statement_split.csv")
    assert len(txs) == 10

    # Debit should produce negative amount
    assert txs[0].raw_description == "GITHUB INC"
    assert txs[0].amount == -25.0

    # Credit (refund or income) should produce positive amount
    stripe_tx = next(t for t in txs if "STRIPE" in t.raw_description)
    assert stripe_tx.amount == 8500.0


def test_parse_missing_required_column_raises_error():
    bad_csv = b"ColA,ColB,ColC\n1,2,3\n"
    with pytest.raises(ValueError) as excinfo:
        parse_csv(bad_csv, "bad.csv")
    assert "Missing required" in str(excinfo.value)


def test_parse_empty_content():
    txs, warnings = parse_csv(b"", "empty.csv")
    assert len(txs) == 0
    assert len(warnings) > 0


def test_parse_header_only():
    header_only = b"Date,Description,Amount\n"
    txs, warnings = parse_csv(header_only, "header_only.csv")
    assert len(txs) == 0
    assert any("no transaction rows" in w for w in warnings)


def test_parse_whitespace_in_headers():
    csv_text = b"  Date  ,  Description  ,  Amount  \n2024-10-01,TEST VENDOR,-42.50\n"
    txs, warnings = parse_csv(csv_text, "spaces.csv")
    assert len(txs) == 1
    assert txs[0].raw_description == "TEST VENDOR"
    assert txs[0].amount == -42.50


def test_parse_semicolon_delimited():
    csv_text = b"Date;Description;Amount\n2024-10-01;TEST VENDOR;-99.00\n"
    txs, warnings = parse_csv(csv_text, "semi.csv")
    assert len(txs) == 1
    assert txs[0].amount == -99.00


def test_parse_parentheses_negative_amounts():
    csv_text = b"Date,Description,Amount\n2024-10-01,TEST ($75.00)\n"
    # Or separate amount column with parentheses
    csv_text2 = b"Date,Description,Amount\n2024-10-01,TEST VENDOR,($75.00)\n"
    txs, warnings = parse_csv(csv_text2, "parens.csv")
    assert len(txs) == 1
    assert txs[0].amount == -75.00
