"""Unit tests for date parsing, monetary validation, and row-level error handling."""

import datetime
from decimal import Decimal
import io
from pathlib import Path
import pytest

from app.services.statement_parser import (
    DateParsingError,
    MonetaryParsingError,
    StatementParser,
    parse_date,
    parse_monetary_amount,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


# -----------------------------------------------------------------------------
# Date Parsing Tests
# -----------------------------------------------------------------------------
def test_parse_iso_dates():
    """Verify standard ISO dates (YYYY-MM-DD and YYYY/MM/DD)."""
    assert parse_date("2026-08-15") == datetime.date(2026, 8, 15)
    assert parse_date("2026/12/31") == datetime.date(2026, 12, 31)


def test_parse_unambiguous_day_first():
    """Verify unambiguous DD/MM/YYYY when day > 12."""
    assert parse_date("25/08/2026") == datetime.date(2026, 8, 25)
    assert parse_date("31-01-2026") == datetime.date(2026, 1, 31)


def test_parse_unambiguous_month_first():
    """Verify unambiguous MM/DD/YYYY when second number > 12."""
    assert parse_date("08/25/2026") == datetime.date(2026, 8, 25)
    assert parse_date("01-31-2026") == datetime.date(2026, 1, 31)


def test_parse_ambiguous_date_rejected_by_default():
    """Verify dates where day and month are both <= 12 raise AMBIGUOUS_DATE without config."""
    with pytest.raises(DateParsingError) as exc_info:
        parse_date("03/04/2026")
    assert exc_info.value.code == "AMBIGUOUS_DATE"


def test_parse_ambiguous_date_with_day_first_config():
    """Verify day_first=True resolves 03/04/2026 to April 3rd."""
    res = parse_date("03/04/2026", day_first=True)
    assert res == datetime.date(2026, 4, 3)


def test_parse_ambiguous_date_with_month_first_config():
    """Verify day_first=False resolves 03/04/2026 to March 4th."""
    res = parse_date("03/04/2026", day_first=False)
    assert res == datetime.date(2026, 3, 4)


def test_parse_custom_date_format():
    """Verify explicit date_format overrides ambiguous parsing."""
    res = parse_date("2026.08.15", date_format="%Y.%m.%d")
    assert res == datetime.date(2026, 8, 15)


def test_impossible_dates_rejected():
    """Verify impossible calendar dates like Feb 30 and April 31 are rejected with INVALID_DATE."""
    with pytest.raises(DateParsingError) as exc1:
        parse_date("2026-02-30")
    assert exc1.value.code == "INVALID_DATE"

    with pytest.raises(DateParsingError) as exc2:
        parse_date("31/04/2026")
    assert exc2.value.code == "INVALID_DATE"


def test_empty_date_rejected():
    """Verify empty date strings are rejected."""
    with pytest.raises(DateParsingError) as exc:
        parse_date("   ")
    assert exc.value.code == "INVALID_DATE"


# -----------------------------------------------------------------------------
# Monetary Parsing Tests
# -----------------------------------------------------------------------------
def test_parse_standard_monetary_amounts():
    """Verify positive and negative Decimal amounts without float conversion."""
    val1, _ = parse_monetary_amount("125.50")
    assert val1 == Decimal("125.50")
    assert isinstance(val1, Decimal)

    val2, _ = parse_monetary_amount("-45.25")
    assert val2 == Decimal("-45.25")


def test_parse_thousands_separators():
    """Verify standard thousands commas are accepted."""
    val, _ = parse_monetary_amount("1,250.00")
    assert val == Decimal("1250.00")

    val_neg, _ = parse_monetary_amount("-10,500.50")
    assert val_neg == Decimal("-10500.50")


def test_improper_thousands_grouping_rejected():
    """Verify non-standard comma grouping is rejected rather than silently misparsed."""
    with pytest.raises(MonetaryParsingError) as exc1:
        parse_monetary_amount("1,25,0.00")
    assert exc1.value.code == "INVALID_AMOUNT"

    with pytest.raises(MonetaryParsingError) as exc2:
        parse_monetary_amount("1,2.00")
    assert exc2.value.code == "INVALID_AMOUNT"


def test_currency_symbols_detection():
    """Verify currency symbols ($, €, £, ¥) are stripped and currency code detected."""
    val_usd, curr_usd = parse_monetary_amount("$125.50")
    assert val_usd == Decimal("125.50")
    assert curr_usd == "USD"

    val_eur, curr_eur = parse_monetary_amount("€45.00")
    assert val_eur == Decimal("45.00")
    assert curr_eur == "EUR"

    val_gbp, curr_gbp = parse_monetary_amount("£99.99")
    assert val_gbp == Decimal("99.99")
    assert curr_gbp == "GBP"


def test_accounting_negative_format():
    """Verify parenthesized negative amounts (45.25) are converted to -45.25."""
    val, _ = parse_monetary_amount("(45.25)")
    assert val == Decimal("-45.25")

    val_curr, curr = parse_monetary_amount("($150.00)")
    assert val_curr == Decimal("-150.00")
    assert curr == "USD"


def test_malformed_amounts_rejected():
    """Verify non-numeric strings and invalid formats raise INVALID_AMOUNT."""
    for bad in ["abc", "12.34.56", "", "None", "NaN", "Infinity", "--50"]:
        with pytest.raises(MonetaryParsingError) as exc:
            parse_monetary_amount(bad)
        assert exc.value.code == "INVALID_AMOUNT"


# -----------------------------------------------------------------------------
# Row-Level Error Isolation Tests
# -----------------------------------------------------------------------------
def test_invalid_dates_fixture_reports_exact_rows():
    """Verify invalid_dates.csv reports errors on row 2, 4, 5 while parsing row 3."""
    parser = StatementParser()
    result = parser.parse_file(FIXTURES_DIR / "invalid_dates.csv")

    assert result.total_rows == 4
    assert result.valid_row_count == 1
    assert result.invalid_row_count == 3

    # Row 3 was valid
    assert result.transactions[0].row_number == 3
    assert result.transactions[0].transaction.original_description == "VALID ENTRY"

    # Check error row numbers and codes
    err_rows = [e.row_number for e in result.errors]
    assert 2 in err_rows
    assert 4 in err_rows
    assert 5 in err_rows


def test_invalid_amounts_fixture_reports_exact_rows():
    """Verify invalid_amounts.csv isolates row errors without halting processing."""
    parser = StatementParser()
    result = parser.parse_file(FIXTURES_DIR / "invalid_amounts.csv")

    assert result.total_rows == 4
    assert result.valid_row_count == 1
    assert result.invalid_row_count == 3

    assert result.transactions[0].row_number == 3
    assert result.transactions[0].transaction.amount == Decimal("-25.00")


def test_both_debit_and_credit_nonzero_rejected():
    """Verify rows with both debit and credit filled are rejected with BOTH_DEBIT_AND_CREDIT."""
    csv_data = (
        "date,description,debit,credit\n"
        "2026-08-01,CONFLICTING ROW,50.00,50.00\n"
        "2026-08-02,VALID DEBIT,25.00,\n"
    )
    parser = StatementParser()
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.total_rows == 2
    assert result.valid_row_count == 1
    assert result.invalid_row_count == 1
    assert any(e.error_code == "BOTH_DEBIT_AND_CREDIT" for e in result.errors)


def test_empty_description_rejected():
    """Verify rows with empty description are rejected with MISSING_DESCRIPTION."""
    csv_data = "date,description,amount\n2026-08-01,,10.00\n"
    parser = StatementParser()
    result = parser.parse_file(io.StringIO(csv_data))

    assert result.valid_row_count == 0
    assert result.invalid_row_count == 1
    assert any(e.error_code == "MISSING_DESCRIPTION" for e in result.errors)
