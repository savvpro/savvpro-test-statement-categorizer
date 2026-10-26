"""
Financial summary computation with strict validation.

Key rules:
- Operating Income: Only verified positive income (amount > 0) is added to total_income.
  Negative amounts with type INCOME are excluded to prevent profit/loss distortion.
- Gross Expenses: Transactions with type EXPENSE → total_expenses (absolute value).
- Matched Refunds: Refunds that are successfully matched to an expense category and
  confirmed/auto-categorized safely reduce gross expenses (matched_refunds).
- Unmatched Refunds: Kept in Needs Review and excluded from operating expense deductions
  until confirmed by the user.
- Internal Transfers: Excluded from operating revenue and expenses.
- Fees: Bank and payment processing fees reduce the net operating result.
- Net Expenses = max(0, total_expenses - matched_refunds)
- Net Operating Result = total_income - net_expenses - total_fees
- Unclassified Impact: Tracks unclassified_amount and flags the summary as provisional
  whenever unresolved transactions remain, making it clear that unresolved items may alter results.

All calculations use Decimal for exact precision.
"""

from decimal import Decimal
from collections import defaultdict

from backend.models import (
    CategorizedTransaction, FinancialSummary,
    TransactionType, BusinessCategory, ReviewStatus,
)


def compute_summary(transactions: list[CategorizedTransaction]) -> FinancialSummary:
    """Compute the financial summary with direction and refund validation."""
    total_income = Decimal("0.00")
    total_expenses = Decimal("0.00")
    total_refunds = Decimal("0.00")
    matched_refunds = Decimal("0.00")
    unmatched_refunds = Decimal("0.00")
    total_transfers = Decimal("0.00")
    total_fees = Decimal("0.00")
    needs_review_count = 0
    unclassified_amount = Decimal("0.00")
    duplicate_count = 0
    category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for tx in transactions:
        cat_key = tx.business_category.value
        amount_abs = abs(tx.amount)

        if tx.is_possible_duplicate:
            duplicate_count += 1

        if tx.review_status == ReviewStatus.NEEDS_REVIEW:
            needs_review_count += 1
            unclassified_amount += amount_abs

        if tx.transaction_type == TransactionType.INCOME:
            # Direction check: operating income must be positive
            if tx.amount > 0:
                total_income += tx.amount
                category_totals[cat_key] += tx.amount

        elif tx.transaction_type == TransactionType.EXPENSE:
            total_expenses += amount_abs
            category_totals[cat_key] += amount_abs

        elif tx.transaction_type == TransactionType.REFUND:
            total_refunds += amount_abs

            # Only safely matched and confirmed/auto refunds reduce operating expenses
            is_matched_and_confirmed = (
                tx.business_category != BusinessCategory.UNKNOWN
                and tx.review_status != ReviewStatus.NEEDS_REVIEW
                and tx.amount > 0
            )

            if is_matched_and_confirmed:
                matched_refunds += amount_abs
                # Net out against the specific expense category total
                category_totals[cat_key] = max(
                    Decimal("0.00"),
                    category_totals[cat_key] - amount_abs,
                )
            else:
                unmatched_refunds += amount_abs

        elif tx.transaction_type == TransactionType.TRANSFER:
            total_transfers += amount_abs
            # Transfers are strictly excluded from operating result

        elif tx.transaction_type == TransactionType.FEE:
            total_fees += amount_abs
            category_totals[cat_key] += amount_abs

    # Net expenses deduction only uses validated matched refunds
    net_expenses = max(Decimal("0.00"), total_expenses - matched_refunds)
    net_operating_result = total_income - net_expenses - total_fees
    is_provisional = (needs_review_count > 0 or unmatched_refunds > Decimal("0.00"))

    return FinancialSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        total_refunds=total_refunds,
        matched_refunds=matched_refunds,
        unmatched_refunds=unmatched_refunds,
        total_transfers=total_transfers,
        total_fees=total_fees,
        net_expenses=net_expenses,
        net_operating_result=net_operating_result,
        transaction_count=len(transactions),
        needs_review_count=needs_review_count,
        unclassified_amount=unclassified_amount,
        duplicate_count=duplicate_count,
        is_provisional=is_provisional,
        category_totals=dict(category_totals),
    )
