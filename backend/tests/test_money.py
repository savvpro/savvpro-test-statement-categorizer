from decimal import Decimal

import pytest

from app.db.money import format_amount, from_cents, to_cents
from app.schemas import TransactionOut


@pytest.mark.parametrize(
    ("value", "cents"),
    [
        ("0", 0),
        ("0.01", 1),
        ("45", 4500),
        ("-45.00", -4500),
        ("1234.56", 123456),
        ("-1234.56", -123456),
        ("99999999999.99", 9999999999999),
    ],
)
def test_round_trip(value: str, cents: int) -> None:
    assert to_cents(Decimal(value)) == cents
    assert from_cents(cents) == Decimal(value)


@pytest.mark.parametrize(
    ("value", "cents"),
    [
        # ROUND_HALF_UP: exact ties move away from zero.
        ("1234.565", 123457),
        ("-1234.565", -123457),
        ("0.005", 1),
        ("-0.005", -1),
        ("1234.564", 123456),
        ("1234.5650001", 123457),
    ],
)
def test_rounding_half_up(value: str, cents: int) -> None:
    assert to_cents(value) == cents


def test_from_cents_keeps_two_places() -> None:
    assert str(from_cents(4500)) == "45.00"
    assert str(from_cents(-5)) == "-0.05"


@pytest.mark.parametrize(
    ("value", "text"),
    [("45", "45.00"), ("-0.001", "0.00"), ("-45.5", "-45.50"), ("1E+3", "1000.00")],
)
def test_format_amount(value: str, text: str) -> None:
    assert format_amount(Decimal(value)) == text


@pytest.mark.parametrize("bad", [1.5, True])
def test_rejects_float_and_bool(bad: object) -> None:
    with pytest.raises(TypeError):
        to_cents(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", ["abc", "NaN", "Infinity"])
def test_rejects_non_finite_or_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        to_cents(bad)


def test_schema_serializes_amount_as_string() -> None:
    payload = {
        "id": 1,
        "statement_id": 1,
        "row_index": 0,
        "date": "2025-01-15",
        "description_raw": "FAKE STUDIO SUPPLY",
        "merchant_key": "FAKE STUDIO SUPPLY",
        "amount": Decimal("-12.5"),
        "category_id": "office_supplies",
        "suggested_category_id": None,
        "confidence": 0.9,
        "status": "auto",
        "reasons": [],
        "rule_id": None,
        "flags": [],
        "is_pending": False,
        "linked_transaction_id": None,
        "updated_at": "2025-01-15T00:00:00Z",
    }

    dumped = TransactionOut.model_validate(payload).model_dump(mode="json")

    assert dumped["amount"] == "-12.50"
