"""Unit tests for date parsing and ambiguity detection."""
from datetime import date

import pytest

from app.ingest.dates import infer_date_order, parse_date


@pytest.mark.parametrize(
    "value, prefer_mdy, expected",
    [
        ("01/15/2026", True, date(2026, 1, 15)),
        ("15/01/2026", False, date(2026, 1, 15)),
        ("2026-01-15", True, date(2026, 1, 15)),
        ("2026-01-15", False, date(2026, 1, 15)),  # ISO always works
        ("Jan 15 2026", True, date(2026, 1, 15)),
        ("15 Jan 2026", True, date(2026, 1, 15)),
        ("January 15, 2026", True, date(2026, 1, 15)),
        ("01/15/26", True, date(2026, 1, 15)),
        ("03/25/2026", True, date(2026, 3, 25)),
    ],
)
def test_parse_date(value: str, prefer_mdy: bool, expected: date) -> None:
    assert parse_date(value, prefer_mdy=prefer_mdy) == expected


def test_parse_date_invalid_raises() -> None:
    with pytest.raises(ValueError):
        parse_date("not-a-date")


def test_infer_date_order_mdy() -> None:
    # Day > 12 in 2nd position → unambiguously MDY
    dates = ["01/25/2026", "02/18/2026", "03/15/2026"]
    prefer_mdy, ambiguous = infer_date_order(dates)
    assert prefer_mdy is True
    assert ambiguous is False


def test_infer_date_order_dmy() -> None:
    # Day > 12 in 1st position → unambiguously DMY
    dates = ["25/01/2026", "18/02/2026", "15/03/2026"]
    prefer_mdy, ambiguous = infer_date_order(dates)
    assert prefer_mdy is False
    assert ambiguous is False


def test_infer_date_order_ambiguous() -> None:
    # All day/month ≤ 12 → ambiguous
    dates = ["01/02/2026", "03/04/2026", "05/06/2026"]
    prefer_mdy, ambiguous = infer_date_order(dates)
    assert ambiguous is True
