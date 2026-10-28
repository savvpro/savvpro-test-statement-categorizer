from decimal import Decimal

import pytest

from app.ingest.amounts import (
    AmountError,
    detect_decimal_comma,
    format_cents,
    has_extra_precision,
    parse_amount,
    to_cents,
)


@pytest.mark.parametrize(
    ("raw", "cents"),
    [
        ("1234.56", 123456),
        ("1,234.56", 123456),
        ("-45.00", -4500),
        ("(45.00)", -4500),
        ("$45.00", 4500),
        ("-$45.00", -4500),
        ("$-45.00", -4500),
        ("45.00-", -4500),
        ("45.00 CR", 4500),
        ("45.00 DR", -4500),
        ("USD 45.00", 4500),
        ("−45", -4500),
        ("1 234.50", 123450),
        ("1 234.50", 123450),
        ("+7", 700),
        (".5", 50),
    ],
)
def test_P09_amount_formats(raw: str, cents: int) -> None:
    assert to_cents(parse_amount(raw)) == cents


def test_P03_decimal_comma_parse() -> None:
    assert to_cents(parse_amount("1.234,56", decimal_comma=True)) == 123456
    assert to_cents(parse_amount("-45,5", decimal_comma=True)) == -4550


def test_P03_decimal_comma_detection_is_column_level() -> None:
    assert detect_decimal_comma(["1.234,56", "-45,00", "10,5"])
    assert not detect_decimal_comma(["1,234.56", "-45.00"])
    assert not detect_decimal_comma(["1.234,56", "45.00"])  # mixed -> not consistent
    assert not detect_decimal_comma(["1,234", "2,500"])  # thousands separators only


@pytest.mark.parametrize("raw", ["", "abc", "1.2.3", "12 34 x", "--5", "$", "9" * 30])
def test_bad_amounts_raise(raw: str) -> None:
    with pytest.raises(AmountError):
        parse_amount(raw)


def test_extra_precision_rounds_half_even() -> None:
    value = parse_amount("0.125")
    assert has_extra_precision(value)
    assert to_cents(value) == 12  # banker's rounding
    assert to_cents(Decimal("0.135")) == 14


def test_format_cents_roundtrip() -> None:
    for cents in (0, 5, -5, 100, -123456, 99_999_999):
        assert to_cents(parse_amount(format_cents(cents))) == cents
