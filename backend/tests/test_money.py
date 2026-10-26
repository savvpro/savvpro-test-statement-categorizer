from decimal import Decimal

import pytest

from app.core.money import MoneyError, from_minor, to_minor


@pytest.mark.parametrize(
    ("text", "minor"),
    [
        ("-1850.00", -185000),
        ("185000.00", 18500000),
        ("0", 0),
        ("0.00", 0),
        ("0.01", 1),
        ("-0.01", -1),
        ("12", 1200),
        ("1.5", 150),
        ("1.500", 150),  # trailing zeros are fine
        ("1E+3", 100000),
        ("123456789012.34", 12345678901234),
    ],
)
def test_round_trip_is_exact(text: str, minor: int) -> None:
    assert to_minor(Decimal(text)) == minor
    assert from_minor(minor) == Decimal(text)
    assert str(from_minor(minor)).count(".") == 1  # always two decimals, never "1850"


@pytest.mark.parametrize("text", ["1.005", "-0.001", "0.1234567890123456789012345678901"])
def test_more_than_two_decimals_is_refused_not_rounded(text: str) -> None:
    with pytest.raises(MoneyError):
        to_minor(Decimal(text))


@pytest.mark.parametrize("text", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_is_refused(text: str) -> None:
    with pytest.raises(MoneyError):
        to_minor(Decimal(text))
