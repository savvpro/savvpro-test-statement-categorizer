"""
Tax summary aggregation engine for IRS Schedule C reporting.
Calculates gross income, deductible expenses, net taxable profit,
and estimated tax savings for freelance tech consultants.
"""

from typing import List, Dict
from collections import defaultdict
from app.models.transaction import (
    TransactionCategorized,
    TransactionDirection,
    TaxSummary,
    CategorySummary,
    ReviewStatus,
)
from app.brain.categories import get_category_info

# Standard freelance / self-employment effective marginal tax rate estimate (15.3% SE tax + ~13% federal income tax)
ESTIMATED_SELF_EMPLOYED_TAX_RATE = 0.28


def calculate_tax_summary(transactions: List[TransactionCategorized]) -> TaxSummary:
    """
    Compute comprehensive tax and expense summaries from categorized transactions.
    """
    total_transactions = len(transactions)
    gross_income = 0.0
    total_outflows = 0.0
    total_refunds = 0.0
    total_deductible = 0.0
    non_taxable_transfers = 0.0
    needs_review_count = 0
    needs_review_amount = 0.0

    # Per-category aggregation tracking
    category_counts: Dict[str, int] = defaultdict(int)
    category_gross: Dict[str, float] = defaultdict(float)
    category_deductible: Dict[str, float] = defaultdict(float)

    for tx in transactions:
        # Check review status
        if tx.needs_review or tx.status == ReviewStatus.NEEDS_REVIEW:
            needs_review_count += 1
            needs_review_amount += tx.amount

        # Cash-flow direction calculations
        if tx.direction == TransactionDirection.INFLOW:
            # Only verified inflows count towards verified gross taxable income
            if not tx.needs_review:
                gross_income += tx.amount

        elif tx.direction == TransactionDirection.OUTFLOW:
            total_outflows += tx.amount
            # Deductible expenses: only verified and marked tax deductible
            if tx.tax_deductible and not tx.needs_review:
                total_deductible += tx.deductible_amount

        elif tx.direction == TransactionDirection.REFUND:
            # Refunds reduce total business expenses and deductible expenses
            total_refunds += tx.amount
            if tx.tax_deductible and not tx.needs_review:
                total_deductible -= tx.deductible_amount

        elif tx.direction == TransactionDirection.TRANSFER:
            non_taxable_transfers += tx.amount

        # Category breakdowns
        category_counts[tx.category] += 1
        category_gross[tx.category] += tx.amount
        if tx.tax_deductible and not tx.needs_review:
            if tx.direction == TransactionDirection.REFUND:
                category_deductible[tx.category] -= tx.deductible_amount
            else:
                category_deductible[tx.category] += tx.deductible_amount

    # Net expenses after refund reductions
    net_expenses = max(0.0, total_outflows - total_refunds)
    net_deductible_expenses = max(0.0, total_deductible)

    # Net taxable profit and tax savings
    net_taxable_profit = round(gross_income - net_deductible_expenses, 2)
    estimated_tax_savings = round(
        net_deductible_expenses * ESTIMATED_SELF_EMPLOYED_TAX_RATE, 2
    )

    # Generate category summaries
    categories_list: List[CategorySummary] = []
    total_gross_for_pct = sum(
        amount for cat, amount in category_gross.items()
        if cat not in ("Transfers & Non-Taxable", "Gross Business Income")
    )

    for cat_name, count in category_counts.items():
        gross = round(category_gross[cat_name], 2)
        ded = round(category_deductible[cat_name], 2)
        info = get_category_info(cat_name)

        pct = 0.0
        if total_gross_for_pct > 0 and cat_name not in (
            "Transfers & Non-Taxable",
            "Gross Business Income",
        ):
            pct = round((gross / total_gross_for_pct) * 100.0, 1)

        categories_list.append(
            CategorySummary(
                category=cat_name,
                schedule_c_line=info.get("schedule_c_line", "Line"),
                transaction_count=count,
                gross_amount=gross,
                deductible_amount=ded,
                color=info.get("color", "#94A3B8"),
                percentage=pct,
            )
        )

    # Sort categories by gross amount descending
    categories_list.sort(key=lambda c: c.gross_amount, reverse=True)

    return TaxSummary(
        total_transactions=total_transactions,
        gross_income=round(gross_income, 2),
        total_expenses=round(net_expenses, 2),
        total_deductible_expenses=round(net_deductible_expenses, 2),
        net_taxable_profit=net_taxable_profit,
        estimated_tax_savings=estimated_tax_savings,
        non_taxable_transfers=round(non_taxable_transfers, 2),
        needs_review_count=needs_review_count,
        needs_review_amount=round(needs_review_amount, 2),
        categories=categories_list,
    )
