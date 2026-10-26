"""
Unit tests for IRS Schedule C tax summary calculation.
"""

import pytest
from app.brain.tax_summary import calculate_tax_summary
from app.models.transaction import (
    TransactionCategorized,
    TransactionDirection,
    ReviewStatus,
)


def _make_tx(
    tx_id: str,
    amount: float,
    direction: TransactionDirection,
    category: str,
    deductible_pct: float,
    status: ReviewStatus = ReviewStatus.AUTO_VERIFIED,
    needs_review: bool = False,
    tax_deductible: bool = True,
) -> TransactionCategorized:
    ded_amt = round(amount * deductible_pct, 2) if (tax_deductible and not needs_review) else 0.0
    return TransactionCategorized(
        id=tx_id,
        date="2024-10-01",
        raw_description=f"Tx {tx_id}",
        clean_merchant=f"Merchant {tx_id}",
        amount=amount,
        direction=direction,
        category=category,
        schedule_c_line="Line 1",
        tax_deductible=tax_deductible,
        deductible_percentage=deductible_pct,
        deductible_amount=ded_amt,
        confidence=0.98,
        status=status,
        needs_review=needs_review,
    )


def test_tax_summary_income_and_expense_math():
    txs = [
        # Inflow: $5,000 verified
        _make_tx("1", 5000.0, TransactionDirection.INFLOW, "Gross Business Income", 0.0, tax_deductible=False),
        # Software: $100 outflow (100% deductible)
        _make_tx("2", 100.0, TransactionDirection.OUTFLOW, "Software & Subscriptions", 1.0),
        # Meal: $100 outflow (50% deductible)
        _make_tx("3", 100.0, TransactionDirection.OUTFLOW, "Meals & Client Entertainment", 0.5),
    ]
    summary = calculate_tax_summary(txs)
    assert summary.gross_income == 5000.0
    assert summary.total_expenses == 200.0
    assert summary.total_deductible_expenses == 150.0  # 100 + 50
    assert summary.net_taxable_profit == 4850.0  # 5000 - 150
    assert summary.estimated_tax_savings == round(150.0 * 0.28, 2)


def test_tax_summary_refund_reduces_expenses_not_income():
    txs = [
        _make_tx("1", 1000.0, TransactionDirection.INFLOW, "Gross Business Income", 0.0, tax_deductible=False),
        _make_tx("2", 300.0, TransactionDirection.OUTFLOW, "Software & Subscriptions", 1.0),
        # $50 refund reducing software expense
        _make_tx("3", 50.0, TransactionDirection.REFUND, "Refund / Expense Reduction", 1.0),
    ]
    summary = calculate_tax_summary(txs)
    assert summary.gross_income == 1000.0
    assert summary.total_expenses == 250.0  # 300 - 50
    assert summary.total_deductible_expenses == 250.0  # 300 - 50
    assert summary.net_taxable_profit == 750.0


def test_tax_summary_transfers_excluded_from_profit():
    txs = [
        _make_tx("1", 500.0, TransactionDirection.TRANSFER, "Transfers & Non-Taxable", 0.0, tax_deductible=False),
    ]
    summary = calculate_tax_summary(txs)
    assert summary.gross_income == 0.0
    assert summary.total_expenses == 0.0
    assert summary.total_deductible_expenses == 0.0
    assert summary.non_taxable_transfers == 500.0
    assert summary.net_taxable_profit == 0.0


def test_tax_summary_needs_review_tracking():
    txs = [
        _make_tx("1", 89.99, TransactionDirection.OUTFLOW, "Office Supplies & Books", 1.0,
                 status=ReviewStatus.NEEDS_REVIEW, needs_review=True),
        _make_tx("2", 55.00, TransactionDirection.OUTFLOW, "Needs Review", 0.0,
                 status=ReviewStatus.NEEDS_REVIEW, needs_review=True, tax_deductible=False),
    ]
    summary = calculate_tax_summary(txs)
    assert summary.needs_review_count == 2
    assert summary.needs_review_amount == round(89.99 + 55.00, 2)
    # Needs review items are not counted toward deductible expenses until approved
    assert summary.total_deductible_expenses == 0.0


def test_tax_summary_category_breakdown_percentages():
    txs = [
        _make_tx("1", 300.0, TransactionDirection.OUTFLOW, "Software & Subscriptions", 1.0),
        _make_tx("2", 100.0, TransactionDirection.OUTFLOW, "Travel & Transportation", 1.0),
    ]
    summary = calculate_tax_summary(txs)
    assert len(summary.categories) == 2
    # Software is 300 / 400 = 75%
    soft_cat = next(c for c in summary.categories if c.category == "Software & Subscriptions")
    assert soft_cat.percentage == 75.0
    assert soft_cat.transaction_count == 1
    assert soft_cat.gross_amount == 300.0
    assert soft_cat.deductible_amount == 300.0
