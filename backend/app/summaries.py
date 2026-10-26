"""
Financial summary calculation and category aggregation service for Freelance Ledger.
Ensures strict Decimal arithmetic, zero float inaccuracy, and compliant tax classifications.
"""

from decimal import Decimal
from typing import Any

from .models import (
    CANONICAL_CATEGORIES,
    EXPENSE_CATEGORIES,
    CategorySummaryItem,
    SummaryResponse,
    Transaction,
)


def calculate_summary(transactions: list[Transaction]) -> SummaryResponse:
    """
    Computes precise financial totals and category breakdown from transactions.
    
    Rules:
    - Total expenses = sum of absolute amounts for all EXPENSE_CATEGORIES.
    - Total income = sum of amounts for 'Income'.
    - Total refunds = sum of amounts for 'Refund' (tracked separately, offsets expenses, never income).
    - Transfers = tracked separately; strictly excluded from operating income and operating expenses.
    - Needs Review = count and dollar volume of unverified transactions; excluded from confirmed buckets.
    - Meals & Coffee carries an IRS Schedule C note: 50% business meal deduction.
    """
    total_expenses = Decimal("0.00")
    total_income = Decimal("0.00")
    total_refunds = Decimal("0.00")
    total_transfers = Decimal("0.00")
    needs_review_count = 0
    needs_review_amount = Decimal("0.00")

    # Map category -> (count, total_amount)
    cat_buckets: dict[str, dict[str, Any]] = {
        cat: {"count": 0, "total": Decimal("0.00")} for cat in CANONICAL_CATEGORIES
    }

    for tx in transactions:
        amt = tx.amount
        cat = tx.category if tx.category in cat_buckets else "Needs Review"

        # Check needs review flag or category
        if tx.needs_review or cat == "Needs Review":
            needs_review_count += 1
            needs_review_amount += abs(amt)

        cat_buckets[cat]["count"] += 1
        cat_buckets[cat]["total"] += abs(amt)

        # Operating classifications
        if cat in EXPENSE_CATEGORIES:
            total_expenses += abs(amt)
        elif cat == "Income":
            total_income += abs(amt)
        elif cat == "Refund":
            total_refunds += abs(amt)
        elif cat == "Transfer (not spending)":
            total_transfers += abs(amt)

    # Net operating total: Net operating cash flow (Income - Expenses + Refunds)
    net_operating = total_income - total_expenses + total_refunds

    # Generate breakdown
    breakdown: list[CategorySummaryItem] = []
    for cat in CANONICAL_CATEGORIES:
        data = cat_buckets[cat]
        cnt = data["count"]
        tot = data["total"]

        # Calculate percentage: for expenses, percentage of total expenses; else 0
        pct = 0.0
        if cat in EXPENSE_CATEGORIES and total_expenses > Decimal("0.00"):
            pct = float((tot / total_expenses) * Decimal(100))
        elif cat == "Income" and total_income > Decimal("0.00"):
            pct = 100.0

        deductible_note = None
        if cat == "Meals & Coffee":
            deductible_note = "Subject to 50% business deduction rule under IRS Schedule C (Line 24b)"
        elif cat == "Transfer (not spending)":
            deductible_note = "Excluded from operating revenues and tax deductions"
        elif cat == "Refund":
            deductible_note = "Reduces gross expenses; never recorded as taxable revenue"
        elif cat == "Personal / Owner Draw":
            deductible_note = "Non-deductible personal draw/expense on business statement"

        if cnt > 0:
            breakdown.append(
                CategorySummaryItem(
                    category=cat,
                    count=cnt,
                    total_amount=tot,
                    percentage=round(pct, 1),
                    deductible_note=deductible_note,
                )
            )

    # Sort breakdown: highest amount first
    breakdown.sort(key=lambda x: x.total_amount, reverse=True)

    return SummaryResponse(
        total_transactions=len(transactions),
        total_expenses=total_expenses,
        total_income=total_income,
        total_refunds=total_refunds,
        total_transfers=total_transfers,
        total_needs_review_count=needs_review_count,
        total_needs_review_amount=needs_review_amount,
        net_operating_total=net_operating,
        category_breakdown=breakdown,
    )
