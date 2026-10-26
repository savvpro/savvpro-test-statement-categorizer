from collections import defaultdict
from decimal import Decimal

from app.api.schemas import CurrencySummary, SummaryOut
from app.services.store import Session

# Categories that are not business spending. They are shown separately so they
# never inflate the spend totals.
NON_SPEND = {"Transfer", "Refund", "Credit", "Income", "Personal", "Needs Review"}


def summarize(session: Session) -> SummaryOut:
    spend: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    other: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    needs_review = duplicates = invalid = 0

    for row in session.rows.values():
        txn = row.result.transaction
        if row.is_duplicate:
            duplicates += 1
            continue
        if row.result.needs_review:
            needs_review += 1
        if not txn.is_valid:
            invalid += 1
            continue
        bucket = other if row.result.category in NON_SPEND else spend
        bucket[txn.currency][row.result.category] += txn.amount

    currencies = []
    for cur in sorted(set(spend) | set(other)):
        currencies.append(
            CurrencySummary(
                currency=cur,
                total_spend=sum(spend[cur].values(), Decimal("0")),
                spend_by_category=dict(sorted(spend[cur].items())),
                other_by_category=dict(sorted(other[cur].items())),
            )
        )

    return SummaryOut(
        upload_id=session.id,
        filename=session.filename,
        total_rows=len(session.rows),
        needs_review_count=needs_review,
        duplicate_count=duplicates,
        invalid_count=invalid,
        currencies=currencies,
    )
