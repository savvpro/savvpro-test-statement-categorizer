import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from app.core.parser import parse_amount, parse_csv, parse_date

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample_statement.csv"
HEADER = "Date,Description,Amount,Currency\n"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2026-03-04", dt.date(2026, 3, 4)),
        ("05-Jan-2026", dt.date(2026, 1, 5)),
        ("Jan 5, 2026", dt.date(2026, 1, 5)),
        ("25/03/2026", dt.date(2026, 3, 25)),
        ("03/25/2026", dt.date(2026, 3, 25)),
    ],
)
def test_parse_date_formats(text, expected):
    assert parse_date(text) == expected


def test_ambiguous_date_is_month_first_by_default():
    assert parse_date("03/04/2026") == dt.date(2026, 3, 4)


def test_ambiguous_date_dayfirst_option():
    assert parse_date("03/04/2026", dayfirst=True) == dt.date(2026, 4, 3)


@pytest.mark.parametrize("text", ["", "not-a-date", "2026-02-30"])
def test_invalid_date_raises(text):
    with pytest.raises(ValueError):
        parse_date(text)


@pytest.mark.parametrize(
    "text,amount,currency",
    [
        ("1,234.50", Decimal("1234.50"), None),
        ("(50.00)", Decimal("-50.00"), None),
        ("-12.5", Decimal("-12.5"), None),
        ("$12.99", Decimal("12.99"), "USD"),
        ("\u20ac1.234,50", Decimal("1234.50"), "EUR"),
        ("12,50", Decimal("12.50"), None),
        ("25.00 CR", Decimal("-25.00"), None),
        ("25.00 DR", Decimal("25.00"), None),
        ("GBP 220.00", Decimal("220.00"), "GBP"),
    ],
)
def test_parse_amount_variants(text, amount, currency):
    assert parse_amount(text) == (amount, currency)


@pytest.mark.parametrize("text", ["", "abc", "N/A", "NaN", "1.2.3"])
def test_invalid_amount_raises(text):
    with pytest.raises(ValueError):
        parse_amount(text)


def test_parse_csv_basic():
    txns = parse_csv(HEADER + "2026-01-03,ADOBE CREATIVE CLOUD,54.99,USD\n2026-01-04,UBER *TRIP,(23.40),USD\n")
    assert len(txns) == 2
    assert all(t.is_valid for t in txns)
    assert txns[0].row_number == 2
    assert txns[1].amount == Decimal("-23.40")


def test_empty_rows_are_skipped():
    txns = parse_csv(HEADER + "\n,,,\n2026-01-03,GITHUB,4.00,USD\n\n")
    assert len(txns) == 1


def test_malformed_rows_are_flagged_not_crashing():
    content = HEADER + (
        "not-a-date,DROPBOX,11.99,USD\n"
        "2026-01-03,,19.99,USD\n"
        "2026-01-03,DROPBOX,N/A,USD\n"
        "2026-01-03,X,1.00,USD,extra\n"
        "2026-01-03,GOOD,1.00,USD\n"
    )
    txns = parse_csv(content)
    assert [t.is_valid for t in txns] == [False, False, False, False, True]
    assert all(t.errors for t in txns[:4])


def test_missing_required_columns_raises():
    with pytest.raises(ValueError, match="missing required"):
        parse_csv("Foo,Bar\n1,2\n")


def test_empty_file_raises():
    with pytest.raises(ValueError):
        parse_csv("   \n")


def test_bom_and_semicolon_delimiter():
    content = "\ufeffDate;Description;Amount\n2026-01-03;GITHUB;4,00\n".encode("utf-8")
    txns = parse_csv(content)
    assert len(txns) == 1
    assert txns[0].amount == Decimal("4.00")
    assert txns[0].currency == "USD"


def test_debit_credit_columns():
    txns = parse_csv("Date,Details,Debit,Credit\n2026-01-03,SHOP,10.00,\n2026-01-04,REFUND,,5.00\n")
    assert [t.amount for t in txns] == [Decimal("10.00"), Decimal("-5.00")]


def test_currency_detected_from_symbol():
    txns = parse_csv("Date,Description,Amount\n2026-01-03,HOTEL,\u20ac99.00\n")
    assert txns[0].currency == "EUR"


def test_sample_statement_parses():
    txns = parse_csv(SAMPLE.read_bytes())
    assert len(txns) == 39
    assert sum(1 for t in txns if not t.is_valid) == 3
    assert {"GBP", "EUR"} <= {t.currency for t in txns}
    assert any(t.amount == Decimal("-89.99") for t in txns)
