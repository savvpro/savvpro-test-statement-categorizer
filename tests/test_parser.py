"""Tests for the CSV parser."""

import pytest
from decimal import Decimal
from backend.parser import parse_csv


class TestValidCSV:
    def test_parses_standard_csv(self):
        csv = "Date,Description,Amount\n2024-01-01,Test Payment,100.00\n"
        transactions, warnings = parse_csv(csv)
        assert len(transactions) == 1
        assert transactions[0].description == "Test Payment"
        assert transactions[0].amount == Decimal("100.00")

    def test_handles_negative_amounts(self):
        csv = "Date,Description,Amount\n2024-01-01,Expense,-50.25\n"
        transactions, _ = parse_csv(csv)
        assert transactions[0].amount == Decimal("-50.25")

    def test_strips_dollar_signs_and_commas(self):
        csv = "Date,Description,Amount\n2024-01-01,Big Payment,\"$1,500.00\"\n"
        transactions, _ = parse_csv(csv)
        assert transactions[0].amount == Decimal("1500.00")

    def test_handles_multiple_date_formats(self):
        csv = "Date,Description,Amount\n2024-01-15,Payment,100.00\n"
        transactions, _ = parse_csv(csv)
        assert transactions[0].date.month == 1
        assert transactions[0].date.day == 15

    def test_detects_ambiguous_dates_with_warning(self):
        """03/04/2024 could be March 4 or April 3; should generate a warning."""
        csv = "Date,Description,Amount\n03/04/2024,Ambiguous Date,100.00\n"
        transactions, warnings = parse_csv(csv)
        assert len(transactions) == 1
        assert any("ambiguous" in w.lower() for w in warnings)

    def test_skips_empty_rows_with_warning(self):
        csv = "Date,Description,Amount\n2024-01-01,Payment,100\n,,\n2024-01-02,Other,200\n"
        transactions, warnings = parse_csv(csv)
        assert len(transactions) == 2
        assert any("empty row" in w.lower() for w in warnings)

    def test_handles_bom(self):
        csv_bytes = b"\xef\xbb\xbfDate,Description,Amount\n2024-01-01,Test,100\n"
        transactions, _ = parse_csv(csv_bytes)
        assert len(transactions) == 1

    def test_handles_latin1_encoding_fallback(self):
        # A byte sequence not valid as utf-8, but valid in latin-1 (e.g. Café with 0xe9)
        csv_bytes = b"Date,Description,Amount\n2024-01-01,Caf\xe9 Supplies,-45.00\n"
        transactions, warnings = parse_csv(csv_bytes)
        assert len(transactions) == 1
        assert "Caf" in transactions[0].description


class TestInvalidCSV:
    def test_missing_columns_raises(self):
        csv = "Date,Amount\n2024-01-01,100\n"
        with pytest.raises(ValueError, match="description"):
            parse_csv(csv)

    def test_empty_file_raises(self):
        with pytest.raises(ValueError):
            parse_csv("")

    def test_header_only_raises(self):
        csv = "Date,Description,Amount\n"
        with pytest.raises(ValueError, match="No valid transactions"):
            parse_csv(csv)

    def test_invalid_date_produces_warning(self):
        csv = "Date,Description,Amount\nnot-a-date,Payment,100\n2024-01-01,OK,200\n"
        transactions, warnings = parse_csv(csv)
        assert len(transactions) == 1
        assert any("cannot parse date" in w.lower() for w in warnings)

    def test_invalid_amount_produces_warning(self):
        csv = "Date,Description,Amount\n2024-01-01,Payment,abc\n2024-01-02,OK,200\n"
        transactions, warnings = parse_csv(csv)
        assert len(transactions) == 1
        assert any("not a valid amount" in w.lower() for w in warnings)

    def test_rejects_nan_and_infinity(self):
        """Special Decimal values like NaN and Infinity must be rejected."""
        csv1 = "Date,Description,Amount\n2024-01-01,Bad,NaN\n2024-01-02,OK,100\n"
        transactions, warnings = parse_csv(csv1)
        assert len(transactions) == 1
        assert any("not a finite" in w.lower() or "not a valid" in w.lower() for w in warnings)

        csv2 = "Date,Description,Amount\n2024-01-01,Bad,Infinity\n2024-01-02,OK,100\n"
        transactions, warnings = parse_csv(csv2)
        assert len(transactions) == 1
        assert any("not a finite" in w.lower() or "not a valid" in w.lower() for w in warnings)
