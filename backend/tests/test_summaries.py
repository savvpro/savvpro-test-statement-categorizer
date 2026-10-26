"""
Unit tests for summary calculations, Decimal precision, and Schedule C tax buckets.
"""

from decimal import Decimal

from app.models import Transaction
from app.summaries import calculate_summary


def test_calculate_summary_precision():
    transactions = [
        # Expenses
        Transaction(
            id="1",
            date="2026-01-01",
            original_date="2026-01-01",
            description="ADOBE",
            normalized_description="ADOBE",
            amount=Decimal("-59.99"),
            direction="expense",
            category="Software",
            confidence=0.98,
            reason="Matched Adobe",
        ),
        Transaction(
            id="2",
            date="2026-01-02",
            original_date="2026-01-02",
            description="UBER",
            normalized_description="UBER",
            amount=Decimal("-32.40"),
            direction="expense",
            category="Travel & Transport",
            confidence=0.95,
            reason="Matched Uber",
        ),
        # Income
        Transaction(
            id="3",
            date="2026-01-03",
            original_date="2026-01-03",
            description="CLIENT INVOICE",
            normalized_description="CLIENT INVOICE",
            amount=Decimal("1500.00"),
            direction="income",
            category="Income",
            confidence=0.96,
            reason="Matched client invoice",
        ),
        # Refund (Must offset, not be treated as income)
        Transaction(
            id="4",
            date="2026-01-04",
            original_date="2026-01-04",
            description="OFFICE DEPOT RETURN",
            normalized_description="OFFICE DEPOT RETURN",
            amount=Decimal("45.50"),
            direction="refund",
            category="Refund",
            confidence=0.95,
            reason="Matched refund",
        ),
        # Transfer (Must be excluded from spending and income)
        Transaction(
            id="5",
            date="2026-01-05",
            original_date="2026-01-05",
            description="TRANSFER TO SAVINGS",
            normalized_description="TRANSFER TO SAVINGS",
            amount=Decimal("-500.00"),
            direction="transfer",
            category="Transfer (not spending)",
            confidence=0.98,
            reason="Matched transfer",
        ),
        # Needs Review
        Transaction(
            id="6",
            date="2026-01-06",
            original_date="2026-01-06",
            description="JOES CAFE 9921",
            normalized_description="JOES CAFE 9921",
            amount=Decimal("-22.00"),
            direction="expense",
            category="Needs Review",
            confidence=0.45,
            reason="Ambiguous",
            needs_review=True,
        ),
    ]

    summary = calculate_summary(transactions)

    # Total expenses = 59.99 + 32.40 = 92.39
    assert summary.total_expenses == Decimal("92.39")
    # Total income = 1500.00
    assert summary.total_income == Decimal("1500.00")
    # Total refunds = 45.50 (kept distinct)
    assert summary.total_refunds == Decimal("45.50")
    # Total transfers = 500.00 (excluded from expenses and income)
    assert summary.total_transfers == Decimal("500.00")
    # Needs review count = 1, amount = 22.00
    assert summary.total_needs_review_count == 1
    assert summary.total_needs_review_amount == Decimal("22.00")
    # Net operating = 1500.00 - 92.39 + 45.50 = 1453.11
    assert summary.net_operating_total == Decimal("1453.11")


def test_meals_and_coffee_deductible_note():
    transactions = [
        Transaction(
            id="1",
            date="2026-01-01",
            original_date="2026-01-01",
            description="STARBUCKS",
            normalized_description="STARBUCKS",
            amount=Decimal("-6.50"),
            direction="expense",
            category="Meals & Coffee",
            confidence=0.92,
            reason="Matched Starbucks",
        ),
    ]
    summary = calculate_summary(transactions)
    meal_item = next((item for item in summary.category_breakdown if item.category == "Meals & Coffee"), None)
    assert meal_item is not None
    assert "50% business deduction rule" in meal_item.deductible_note
