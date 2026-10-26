"""Unit tests for duplicate transaction detection service."""

import datetime
from decimal import Decimal
from pathlib import Path
import pytest

from app.schemas.transaction import TransactionInput
from app.services.duplicate_detector import DuplicateDetector
from app.services.statement_parser import StatementParser

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_identical_rows_flagged_as_duplicates():
    """Verify identical transactions on the same date with same description and amount are flagged."""
    detector = DuplicateDetector()
    tx1 = TransactionInput(
        date=datetime.date(2026, 8, 1),
        original_description="COFFEE SHOP CAFE",
        amount=Decimal("-5.50"),
        currency="USD",
    )
    tx2 = TransactionInput(
        date=datetime.date(2026, 8, 1),
        original_description="COFFEE SHOP CAFE",
        amount=Decimal("-5.50"),
        currency="USD",
    )

    dup_rows, warnings = detector.find_duplicates([(2, tx1), (3, tx2)])

    assert dup_rows == {2, 3}
    assert len(warnings) == 2
    assert any("row(s) 3" in w.message for w in warnings if w.row_number == 2)
    assert any("row(s) 2" in w.message for w in warnings if w.row_number == 3)


def test_different_amounts_are_not_duplicates():
    """Verify identical date and merchant with different amounts are NOT duplicates."""
    detector = DuplicateDetector()
    tx1 = TransactionInput(
        date=datetime.date(2026, 8, 1),
        original_description="UBER *TRIP",
        amount=Decimal("-15.00"),
    )
    tx2 = TransactionInput(
        date=datetime.date(2026, 8, 1),
        original_description="UBER *TRIP",
        amount=Decimal("-25.00"),
    )

    dup_rows, warnings = detector.find_duplicates([(2, tx1), (3, tx2)])

    assert len(dup_rows) == 0
    assert len(warnings) == 0


def test_different_dates_are_not_duplicates():
    """Verify recurring charges on different dates are NOT flagged as same-statement duplicates."""
    detector = DuplicateDetector()
    tx1 = TransactionInput(
        date=datetime.date(2026, 8, 1),
        original_description="COFFEE SHOP CAFE",
        amount=Decimal("-5.50"),
    )
    tx2 = TransactionInput(
        date=datetime.date(2026, 8, 2),
        original_description="COFFEE SHOP CAFE",
        amount=Decimal("-5.50"),
    )

    dup_rows, warnings = detector.find_duplicates([(2, tx1), (3, tx2)])

    assert len(dup_rows) == 0
    assert len(warnings) == 0


def test_different_currencies_are_not_duplicates():
    """Verify transactions with different currencies are distinguished."""
    detector = DuplicateDetector()
    tx1 = TransactionInput(
        date=datetime.date(2026, 8, 1),
        original_description="HOSTING BILL",
        amount=Decimal("-50.00"),
        currency="USD",
    )
    tx2 = TransactionInput(
        date=datetime.date(2026, 8, 1),
        original_description="HOSTING BILL",
        amount=Decimal("-50.00"),
        currency="EUR",
    )

    dup_rows, warnings = detector.find_duplicates([(2, tx1), (3, tx2)])

    assert len(dup_rows) == 0


def test_duplicate_fixture_preserves_all_rows(engine):
    """Verify duplicate_transactions.csv retains all rows and flags duplicate rows non-destructively."""
    parser = StatementParser(categorizer=engine)
    result = parser.parse_file(FIXTURES_DIR / "duplicate_transactions.csv")

    assert result.total_rows == 4
    assert result.valid_row_count == 4
    # All 4 rows must be present in transactions list
    assert len(result.transactions) == 4

    # Rows 2 and 3 are on 2026-08-01 for -5.50 -> potential duplicates
    row2 = next(t for t in result.transactions if t.row_number == 2)
    row3 = next(t for t in result.transactions if t.row_number == 3)
    row4 = next(t for t in result.transactions if t.row_number == 4)  # Uber
    row5 = next(t for t in result.transactions if t.row_number == 5)  # 2026-08-02 Coffee

    assert row2.is_potential_duplicate is True
    assert row3.is_potential_duplicate is True
    assert row4.is_potential_duplicate is False
    assert row5.is_potential_duplicate is False

    assert result.duplicate_count == 2
    assert len(result.warnings) == 2
