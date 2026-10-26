from decimal import Decimal

import pytest

from app.parsing.amounts import parse_amount, parse_amount_with_marker


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1234.56", "1234.56"),
        ("$1,234.56", "1234.56"),
        ("1,234,567.89", "1234567.89"),
        ("-45.00", "-45.00"),
        ("45.00-", "-45.00"),
        ("(45.00)", "-45.00"),
        ("($45.00)", "-45.00"),
        ("-$45.00", "-45.00"),
        ("$-45.00", "-45.00"),
        ("+45.00", "45.00"),
        ("45.00 CR", "45.00"),
        ("45.00cr", "45.00"),
        ("45.00 DR", "-45.00"),
        ("$1,234.56 DR", "-1234.56"),
        ("\u221245.00", "-45.00"),  # unicode minus sign
        ("\u201345.00", "-45.00"),  # en dash used as minus
        ("  45.00  ", "45.00"),
        ("1 234.56", "1234.56"),
        ("\u00a045.00", "45.00"),  # non-breaking space
        ("\u20ac12.50", "12.50"),
        ("\u00a39.99", "9.99"),
        ("45", "45"),
        (".99", "0.99"),
        ("0.00", "0.00"),
        ("1234.565", "1234.565"),  # no rounding here; that happens at the money boundary
    ],
)
def test_parse_amount(text: str, expected: str) -> None:
    result = parse_amount(text)

    assert isinstance(result, Decimal)
    assert result == Decimal(expected)
    assert str(result) == expected  # exact digits preserved, nothing went through float


@pytest.mark.parametrize("text", ["", "   ", "-", "--"])
def test_empty_is_none(text: str) -> None:
    assert parse_amount(text) is None


@pytest.mark.parametrize(
    "text",
    ["abc", "45,00", "1.2.3", "12,34.56", "--45", "(45.00)-", "-45.00 CR", "4 5x", "$", "1e5"],
)
def test_garbage_raises(text: str) -> None:
    with pytest.raises(ValueError, match="invalid amount"):
        parse_amount(text)


def test_marker_is_reported() -> None:
    assert parse_amount_with_marker("45.00 CR") == (Decimal("45.00"), "CR")
    assert parse_amount_with_marker("45.00") == (Decimal("45.00"), None)
