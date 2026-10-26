from itertools import groupby

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.brain.classifier import classify
from app.brain.models import Decision
from app.brain.postcheck import postcheck
from app.core.domain import DEFAULT_KIND_BY_CATEGORY, NEEDS_REVIEW
from app.models import Statement, Transaction, UserRuleRow
from app.schemas import CorrectionOut, TransactionOut
from app.services.errors import NotFoundError, UnprocessableError
from app.services.statements import apply_decision, load_user_rules, to_parsed_row, utcnow


def correct_transaction(
    db: Session,
    transaction_id: int,
    category: str,
    kind: str | None = None,
    remember: bool = False,
) -> CorrectionOut:
    """Set a row's category by hand. With remember, save a user rule for the merchant and
    re-classify every other row of that merchant that the user has not fixed by hand."""
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise NotFoundError(f"Transaction {transaction_id} not found")
    if category == NEEDS_REVIEW:
        raise UnprocessableError("Pick a real category: a fixed row cannot stay in Needs Review")
    if remember and not transaction.merchant_key:
        raise UnprocessableError(
            "Cannot remember this merchant: the description has no usable merchant name"
        )

    implied_kind = DEFAULT_KIND_BY_CATEGORY.get(category)
    sign_kind = "income" if transaction.amount_minor > 0 else "expense"
    transaction.category = category
    transaction.kind = kind or implied_kind or sign_kind
    transaction.confidence = 1.0
    transaction.rule_id = "manual"
    transaction.reason = "set by you"
    transaction.needs_review = False
    transaction.suggested_category = None
    transaction.edited_by_user = True

    reclassified = 0
    if remember:
        _save_user_rule(db, transaction.merchant_key, category, kind or implied_kind)
        db.flush()
        reclassified = _reclassify_merchant(db, transaction.merchant_key)
    db.commit()
    return CorrectionOut(
        transaction=TransactionOut.from_row(transaction), reclassified_count=reclassified
    )


def _save_user_rule(db: Session, merchant_key: str, category: str, kind: str | None) -> None:
    rule = db.scalar(select(UserRuleRow).where(UserRuleRow.merchant_key == merchant_key))
    if rule is None:
        db.add(
            UserRuleRow(
                merchant_key=merchant_key, category=category, kind=kind, created_at=utcnow()
            )
        )
    else:
        rule.category = category
        rule.kind = kind


def _stored_decision(t: Transaction) -> Decision:
    return Decision(
        category=t.category,  # type: ignore[arg-type]
        kind=t.kind,  # type: ignore[arg-type]
        confidence=t.confidence,
        rule_id=t.rule_id,
        reason=t.reason,
        needs_review=t.needs_review,
        suggested_category=t.suggested_category,  # type: ignore[arg-type]
    )


def _reclassify_merchant(db: Session, merchant_key: str) -> int:
    """Re-run the brain for every row of this merchant, in every statement, except rows the
    user fixed by hand. Duplicates share a merchant key, so the duplicate check still sees all
    of them. Returns how many rows actually changed."""
    user_rules = load_user_rules(db)
    transactions = list(
        db.scalars(
            select(Transaction)
            .where(Transaction.merchant_key == merchant_key)
            .order_by(Transaction.statement_id, Transaction.row_number)
        )
    )
    changed = 0
    for statement_id, group_iter in groupby(transactions, key=lambda t: t.statement_id):
        group = list(group_iter)
        account_type = db.get(Statement, statement_id).account_type  # type: ignore[union-attr]
        rows = [to_parsed_row(t, account_type) for t in group]
        decisions = [
            _stored_decision(t) if t.edited_by_user else classify(row, user_rules)
            for t, row in zip(group, rows, strict=True)
        ]
        for t, decision in zip(group, postcheck(rows, decisions), strict=True):
            if t.edited_by_user:
                continue
            before = (t.category, t.kind, t.needs_review, t.rule_id, t.reason)
            apply_decision(t, decision)
            changed += before != (t.category, t.kind, t.needs_review, t.rule_id, t.reason)
    return changed
