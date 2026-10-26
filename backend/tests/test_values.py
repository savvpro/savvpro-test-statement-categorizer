from datetime import date
from decimal import Decimal

import pytest

from app.ingest.values import detect_date_format, parse_amount, try_parse_date


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("45.20", "45.20"),
        ("-45.20", "-45.20"),
        ("$1,234.56", "1234.56"),
        ("-$5", "-5.00"),
        ("$-5.00", "-5.00"),
        ("(12.00)", "-12.00"),
        ("12.00-", "-12.00"),
        ("45.00 CR", "45.00"),
        ("45.00 DR", "-45.00"),
        ("1.234,56", "1234.56"),
        ("12,50", "12.50"),
        ("1,234", "1234.00"),
        ("USD 10", "10.00"),
        ("−10.00", "-10.00"),  # unicode minus sign
        ("+7.10", "7.10"),
    ],
)
def test_parse_amount_formats(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["", "   ", None, "-", "--"])
def test_parse_amount_empty_is_none(raw):
    assert parse_amount(raw) is None


@pytest.mark.parametrize("raw", ["abc", "12.3.4", "N/A"])
def test_parse_amount_rejects_text(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


def test_detect_us_date_format_with_time_suffix():
    fmt, warnings = detect_date_format(["01/13/2026 10:31 AM", "02/01/2026", "03/30/2026"])
    assert fmt == "%m/%d/%Y"
    assert warnings == []
    assert try_parse_date("01/13/2026 10:31 AM", fmt) == date(2026, 1, 13)


def test_detect_day_first_dates_when_day_exceeds_12():
    fmt, _ = detect_date_format(["13/01/2026", "28/02/2026", "05/03/2026"])
    assert fmt == "%d/%m/%Y"
    assert try_parse_date("05/03/2026", fmt) == date(2026, 3, 5)


def test_ambiguous_dates_warn_and_assume_us():
    fmt, warnings = detect_date_format(["01/02/2026", "03/04/2026"])
    assert fmt == "%m/%d/%Y"
    assert warnings and "month/day" in warnings[0]


def test_iso_and_text_dates():
    assert detect_date_format(["2026-01-05", "2026-02-11"])[0] == "%Y-%m-%d"
    assert detect_date_format(["Jan 05, 2026", "Feb 11, 2026"])[0] == "%b %d, %Y"


def test_unreadable_dates():
    assert detect_date_format(["yesterday", "soon"])[0] is None
