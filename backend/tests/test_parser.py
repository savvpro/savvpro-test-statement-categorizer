import pytest
from app.parser import CSVValidationError, parse_csv_content
from app.models import Category


def test_parse_valid_standard_csv():
    csv_data = b"""Date,Description,Amount
2026-03-01,ADOBE CREATIVE CLOUD,-54.99
2026-03-02,UBER TRIP,-28.45
2026-03-03,STRIPE PAYOUT,1200.00
"""
    transactions, warnings = parse_csv_content(csv_data)
    assert len(transactions) == 3
    assert transactions[0].category == Category.SOFTWARE
    assert transactions[0].amount == -54.99
    assert transactions[1].category == Category.TRAVEL
    assert transactions[2].category == Category.INCOME
    assert transactions[2].amount == 1200.00


def test_parse_debit_credit_format():
    csv_data = b"""Date,Description,Debit,Credit
2026-03-01,ADOBE CREATIVE CLOUD,54.99,
2026-03-02,PAYPAL DEPOSIT,,1500.00
2026-03-03,AIRLINE REFUND,,75.00
"""
    transactions, warnings = parse_csv_content(csv_data)
    assert len(transactions) == 3
    assert transactions[0].amount == -54.99
    assert transactions[1].amount == 1500.00
    assert transactions[2].amount == 75.00
    assert transactions[2].category == Category.REFUND


def test_duplicate_rows_preserved():
    # Duplicates should NEVER be discarded
    csv_data = b"""Date,Description,Amount
2026-03-01,STARBUCKS #1042,-5.50
2026-03-01,STARBUCKS #1042,-5.50
"""
    transactions, warnings = parse_csv_content(csv_data)
    assert len(transactions) == 2
    assert transactions[0].id != transactions[1].id
    assert transactions[0].amount == -5.50
    assert transactions[1].amount == -5.50


def test_empty_description_handling():
    csv_data = b"""Date,Description,Amount
2026-03-01,, -40.00
"""
    transactions, warnings = parse_csv_content(csv_data)
    assert len(transactions) == 1
    assert transactions[0].category == Category.NEEDS_REVIEW
    assert len(warnings) == 1


def test_missing_date_column():
    csv_data = b"""Description,Amount
ADOBE,-54.99
"""
    with pytest.raises(CSVValidationError) as exc:
        parse_csv_content(csv_data)
    assert "Missing required Date column" in str(exc.value)


def test_missing_amount_columns():
    csv_data = b"""Date,Description
2026-03-01,ADOBE
"""
    with pytest.raises(CSVValidationError) as exc:
        parse_csv_content(csv_data)
    assert "Missing Amount column(s)" in str(exc.value)


def test_empty_csv():
    with pytest.raises(CSVValidationError) as exc:
        parse_csv_content(b"")
    assert "Uploaded CSV file is empty" in str(exc.value)


def test_invalid_date_format():
    csv_data = b"""Date,Description,Amount
invalid-date,ADOBE,-54.99
"""
    with pytest.raises(CSVValidationError) as exc:
        parse_csv_content(csv_data)
    assert "Unable to parse date" in str(exc.value)


def test_invalid_amount_format():
    csv_data = b"""Date,Description,Amount
2026-03-01,ADOBE,not-a-number
"""
    with pytest.raises(CSVValidationError) as exc:
        parse_csv_content(csv_data)
    assert "Invalid amount value" in str(exc.value)


def test_parenthesis_negative_and_currency_symbols():
    csv_data = b"""Date,Description,Amount
2026-03-01,STAPLES,"($1,250.75)"
2026-03-02,CLIENT REVENUE,"$2,500.00"
"""
    transactions, _ = parse_csv_content(csv_data)
    assert transactions[0].amount == -1250.75
    assert transactions[1].amount == 2500.00
