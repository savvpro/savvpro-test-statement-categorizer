"""Totals for the review screen and for tax time."""

from collections.abc import Iterable
from decimal import Decimal

from ..categories import DEDUCTIBLE, KIND, Category, Kind
from ..models import CategoryTotal, Summary, TaxSummary, Transaction

ZERO = Decimal("0.00")


def _sum(amounts: Iterable[Decimal]) -> Decimal:
    return sum(amounts, ZERO)


def summarize(transactions: list[Transaction]) -> Summary:
    counts: dict[Category, int] = {}
    totals: dict[Category, Decimal] = {}
    for t in transactions:
        counts[t.category] = counts.get(t.category, 0) + 1
        totals[t.category] = totals.get(t.category, ZERO) + t.amount

    by_category = [
        CategoryTotal(category=c, kind=KIND[c], count=counts[c], total=totals[c])
        for c in Category  # fixed order, so the UI does not jump around
        if c in counts
    ]

    income = _sum(t.amount for t in transactions if t.category is Category.INCOME)
    deductible_gross = -_sum(t.amount for t in transactions if t.category in DEDUCTIBLE)
    personal = -_sum(t.amount for t in transactions if t.category is Category.PERSONAL)
    refunds = [t for t in transactions if t.category is Category.REFUND]
    refunds_netted = _sum(r.amount for r in refunds if r.related_category in DEDUCTIBLE)
    other_refunds = _sum(r.amount for r in refunds) - refunds_netted
    deductible_net = deductible_gross - refunds_netted
    not_spending = _sum(t.amount for t in transactions if KIND[t.category] is Kind.EXCLUDED)

    review = [t for t in transactions if t.category is Category.NEEDS_REVIEW]
    return Summary(
        total_transactions=len(transactions),
        needs_review=len(review),
        by_category=by_category,
        tax=TaxSummary(
            income=income,
            deductible_expenses=deductible_net,
            refunds_netted=refunds_netted,
            personal_spending=personal,
            other_refunds=other_refunds,
            not_spending=not_spending,
            estimated_profit=income - deductible_net,
            needs_review_count=len(review),
            needs_review_in=_sum(t.amount for t in review if t.amount > 0),
            needs_review_out=-_sum(t.amount for t in review if t.amount < 0),
            complete=not review,
        ),
    )
