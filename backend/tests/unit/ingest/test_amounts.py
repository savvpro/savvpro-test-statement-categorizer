"""Unit tests for amount parsing."""
import pytest

from app.ingest.amounts import parse_amount, parse_debit_credit


@pytest.mark.parametrize(
    "raw, expected_cents",
    [
        # Standard
        ("12.34", 1234),
        ("-12.34", -1234),
        ("$12.34", 1234),
        ("$1,234.56", 123456),
        # Parentheses = negative
        ("(12.34)", -1234),
        ("($1,234.56)", -123456),
        # Trailing minus
        ("12.34-", -1234),
        # CR/DR suffix
        ("12.34 CR", 1234),
        ("12.34 DR", -1234),
        # Zero
        ("0.00", 0),
        ("$0", 0),
        # Large
        ("10,000.00", 1_000_000),
    ],
)
def test_parse_amount(raw: str, expected_cents: int) -> None:
    assert parse_amount(raw) == expected_cents


def test_parse_amount_empty_raises() -> None:
    with pytest.raises(ValueError):
        parse_amount("")


def test_parse_amount_garbage_raises() -> None:
    with pytest.raises(ValueError):
        parse_amount("N/A")


@pytest.mark.parametrize(
    "debit, credit, expected",
    [
        ("12.34", "", -1234),  # debit only → negative
        ("", "12.34", 1234),   # credit only → positive
        ("50.00", "50.00", 0), # both same → net 0
    ],
)
def test_parse_debit_credit(debit: str, credit: str, expected: int) -> None:
    assert parse_debit_credit(debit, credit) == expected
