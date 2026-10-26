import datetime as dt

import pytest

from app.parser.normalizer import normalize_description, parse_amount, parse_date


def test_date_iso():
    assert parse_date("2026-10-02") == dt.date(2026, 10, 2)


def test_date_us_format_is_month_first():
    assert parse_date("10/02/2026") == dt.date(2026, 10, 2)


def test_date_falls_back_to_day_first():
    assert parse_date("25/10/2026") == dt.date(2026, 10, 25)


def test_date_invalid_raises():
    with pytest.raises(ValueError):
        parse_date("not-a-date")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("-54.99", -54.99),
        ("29.99", 29.99),
        ("1,200.00", 1200.0),
        ("(45.00)", -45.0),
        ("45.00-", -45.0),
        ("$10", 10.0),
    ],
)
def test_amount_formats(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "", "nan", "inf"])
def test_amount_invalid_raises(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


def test_description_removes_ids_and_symbols():
    assert normalize_description("UBER *TRIP 8821") == "UBER TRIP"
    assert normalize_description("STARBUCKS #4412") == "STARBUCKS"


def test_description_uppercases_and_trims():
    assert normalize_description("  joes   cafe 9921 ") == "JOES CAFE"