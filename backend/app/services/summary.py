from app.brain.result import INCOME, NEEDS_REVIEW, REFUND
from app.schemas import CategoryTotal, Summary, Transaction


def build_summary(transactions: list[Transaction], rules: dict) -> Summary:
    excluded = set(rules["excluded_categories"])
    buckets: dict[str, dict] = {}

    for t in transactions:
        b = buckets.setdefault(t.category, {"count": 0, "total": 0.0})
        b["count"] += 1
        b["total"] += t.amount

    by_category = [
        CategoryTotal(
            category=cat, count=b["count"], total=round(b["total"], 2),
            counted=cat not in excluded,
        )
        for cat, b in sorted(buckets.items())
    ]

    non_expense = excluded | {INCOME, REFUND, NEEDS_REVIEW}
    income = sum(t.amount for t in transactions if t.category == INCOME)
    refunds = sum(t.amount for t in transactions if t.category == REFUND)
    expenses = -sum(t.amount for t in transactions if t.category not in non_expense)

    return Summary(
        by_category=by_category,
        income=round(income, 2),
        expenses=round(expenses, 2),
        refunds=round(refunds, 2),
        net_expenses=round(expenses - refunds, 2),  # refund kharche se minus
        needs_review_count=sum(1 for t in transactions if t.category == NEEDS_REVIEW),
    )