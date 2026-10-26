"""Per-category totals and headline numbers for a statement."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.models import Kind, Transaction

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class CategoryTotal:
    category_id: str
    category_name: str
    kind: Kind
    count: int
    total: Decimal  # spend sign: refunds reduce a category's total


@dataclass(frozen=True)
class Summary:
    totals: tuple[CategoryTotal, ...]
    total_spending: Decimal
    total_refunds: Decimal
    net_spending: Decimal
    excluded_total: Decimal
    income_total: Decimal
    needs_review_count: int
    transaction_count: int


def summarize(transactions: Sequence[Transaction]) -> Summary:
    buckets: dict[str, list[Transaction]] = {}
    for t in transactions:
        buckets.setdefault(t.category_id, []).append(t)

    totals = [
        CategoryTotal(
            category_id=cid,
            category_name=items[0].category_name,
            kind=items[0].kind,
            count=len(items),
            total=sum((t.spend_amount for t in items), ZERO),
        )
        for cid, items in buckets.items()
    ]
    totals.sort(key=lambda c: (c.total, c.category_name), reverse=True)

    expense = [t for t in transactions if t.kind is Kind.EXPENSE]
    spending = sum((t.spend_amount for t in expense if t.spend_amount > 0), ZERO)
    refunds = -sum((t.spend_amount for t in expense if t.spend_amount < 0), ZERO)

    return Summary(
        totals=tuple(totals),
        total_spending=spending,
        total_refunds=refunds,
        net_spending=spending - refunds,
        excluded_total=sum(
            (abs(t.spend_amount) for t in transactions if t.kind is Kind.NON_SPENDING), ZERO
        ),
        income_total=-sum((t.spend_amount for t in transactions if t.kind is Kind.INCOME), ZERO),
        needs_review_count=sum(1 for t in transactions if t.kind is Kind.REVIEW),
        transaction_count=len(transactions),
    )
