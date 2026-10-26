"""Totals per category: what the landlord hands to their accountant.

Amounts are signed (money out is negative), so a refund correctly shrinks
an expense. A transaction that has splits (a mortgage payment) contributes
its parts, never its whole, so nothing is counted twice.
"""
from decimal import Decimal

from pydantic import BaseModel

from app.models import CategorizedTransaction, Category


class CategoryTotal(BaseModel):
    category: Category
    total: Decimal
    count: int


class Summary(BaseModel):
    totals: list[CategoryTotal]
    transaction_count: int
    needs_review_count: int
    duplicate_count: int


def build_summary(transactions: list[CategorizedTransaction]) -> Summary:
    sums: dict[Category, Decimal] = {}
    counts: dict[Category, int] = {}

    def add(category: Category, amount: Decimal) -> None:
        sums[category] = sums.get(category, Decimal("0")) + amount
        counts[category] = counts.get(category, 0) + 1

    for tx in transactions:
        if tx.splits:
            for part in tx.splits:
                add(part.category, part.amount)
        else:
            add(tx.category, tx.amount)

    totals = [
        CategoryTotal(category=category, total=sums[category], count=counts[category])
        for category in Category  # enum order keeps the output stable
        if category in sums
    ]
    return Summary(
        totals=totals,
        transaction_count=len(transactions),
        needs_review_count=sum(tx.needs_review for tx in transactions),
        duplicate_count=sum(tx.is_duplicate for tx in transactions),
    )