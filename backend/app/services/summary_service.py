"""Totals for one statement, in the shape a freelancer (or their accountant) reads them.

- Pending rows are excluded from everything except the pending counters.
- needs_review rows are counted, not totalled: they have no category yet.
- A refund linked to a purchase nets against that purchase's category; an unlinked refund is
  reported on its own and never counted as income.
- Deductible = |net expense| x the category's deductible_pct (meals are 50%).
"""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.brain.models import CategoryKind, TxnStatus
from app.brain.taxonomy import get_category
from app.db.models import Statement, Transaction
from app.db.money import quantize
from app.schemas import CategoryTotal, SummaryOut
from app.services.errors import NotFound

REFUND = "refund"
ZERO = Decimal("0.00")


def _refund_target(txn: Transaction) -> str | None:
    """The expense category a refund nets against, or None if it stands alone."""
    linked = txn.linked_transaction
    if linked is None or linked.status is TxnStatus.needs_review or linked.is_pending:
        return None
    return (
        linked.category_id
        if get_category(linked.category_id).kind is CategoryKind.expense
        else None
    )


def summarize(db: Session, statement_id: int) -> SummaryOut:
    statement = db.get(Statement, statement_id)
    if statement is None:
        raise NotFound(f"statement {statement_id} not found")

    totals: dict[str, Decimal] = defaultdict(Decimal)
    counts: dict[str, int] = defaultdict(int)
    unlinked_refunds, unlinked_count = ZERO, 0
    review_count, review_amount = 0, ZERO
    pending_count, pending_amount = 0, ZERO

    for txn in statement.transactions:
        amount = txn.amount
        if txn.is_pending:
            pending_count += 1
            pending_amount += amount
            continue
        if txn.status is TxnStatus.needs_review:
            review_count += 1
            review_amount += abs(amount)
            continue
        if txn.category_id == REFUND:
            target = _refund_target(txn)
            if target is None:
                unlinked_refunds += amount
                unlinked_count += 1
            else:
                totals[target] += amount
            continue
        totals[txn.category_id] += amount
        counts[txn.category_id] += 1

    operating: list[CategoryTotal] = []
    non_operating: list[CategoryTotal] = []
    income = expenses = deductible = ZERO
    for category_id in sorted(totals, key=lambda c: (totals[c], c)):
        category = get_category(category_id)
        total = quantize(totals[category_id])
        row_deductible = ZERO
        if category.kind is CategoryKind.expense:
            spent = max(-total, ZERO)
            expenses += spent
            row_deductible = quantize(spent * category.deductible_pct / 100)
            deductible += row_deductible
        elif category.kind is CategoryKind.income:
            income += total
        line = CategoryTotal(
            category_id=category_id,
            label=category.label,
            kind=category.kind,
            schedule_c_line=category.schedule_c_line,
            count=counts[category_id],
            total=total,
            deductible=row_deductible,
        )
        bucket = non_operating if category.kind is CategoryKind.non_operating else operating
        bucket.append(line)

    return SummaryOut(
        statement_id=statement.id,
        income=income,
        expenses=expenses,
        net=income - expenses,
        estimated_deductible=deductible,
        categories=operating,
        non_operating=non_operating,
        unlinked_refunds=unlinked_refunds,
        unlinked_refund_count=unlinked_count,
        needs_review_count=review_count,
        needs_review_amount=review_amount,
        pending_count=pending_count,
        pending_amount=pending_amount,
    )
