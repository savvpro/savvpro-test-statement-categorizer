from collections import defaultdict
from decimal import Decimal

from .schemas import NEEDS_REVIEW, CategoryTotal, Summary, Transaction

NOT_SPENDING = {"Income", "Transfer", "Refund"}


def summarize(transactions: list[Transaction]) -> Summary:
    by_id = {t.id: t for t in transactions}
    net: dict[str, Decimal] = defaultdict(Decimal)
    count: dict[str, int] = defaultdict(int)
    income = spending = Decimal(0)
    for tx in transactions:
        count[tx.category] += 1
        target = by_id.get(tx.refund_of) if tx.category == "Refund" else None
        # A matched refund offsets the category of the purchase it pays back.
        bucket = target.category if target else tx.category
        net[bucket] += tx.amount
        if tx.category == "Income":
            income += tx.amount
        elif bucket not in NOT_SPENDING and (tx.amount < 0 or target is not None):
            spending -= tx.amount
    for category in count:
        net.setdefault(category, Decimal(0))
    return Summary(
        categories=[CategoryTotal(category=c, count=count.get(c, 0), net=net[c]) for c in net],
        total_income=income,
        total_spending=spending,
        needs_review_count=count[NEEDS_REVIEW],
    )
