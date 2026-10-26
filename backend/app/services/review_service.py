"""A human sets a category; optionally remember it for the merchant and re-apply it."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.brain.models import TxnStatus
from app.brain.taxonomy import NEEDS_REVIEW, is_valid_category
from app.db.models import MerchantRule, Statement, Transaction
from app.services.categorization import (
    apply_decision,
    learned_rules,
    recategorize,
    rule_hit,
)
from app.services.errors import InvalidCategory, NotFound


def get_transaction(db: Session, txn_id: int) -> Transaction:
    txn = db.get(Transaction, txn_id)
    if txn is None:
        raise NotFound(f"transaction {txn_id} not found")
    return txn


def update_category(
    db: Session, txn_id: int, category_id: str, remember: bool
) -> tuple[Transaction, int]:
    """Returns the confirmed transaction and how many other transactions the rule changed."""
    if not is_valid_category(category_id) or category_id == NEEDS_REVIEW:
        raise InvalidCategory(f"unknown category {category_id!r}")
    txn = get_transaction(db, txn_id)

    txn.category_id = category_id
    txn.status = TxnStatus.user_confirmed
    txn.confidence = 1.0
    txn.suggested_category_id = None
    txn.reasons = ["set by user"]
    txn.rule_id = None

    updated = 0
    if remember:
        rule = upsert_rule(db, txn.merchant_key, category_id)
        db.flush()
        updated = reapply_rule(db, rule)
    db.commit()
    return txn, updated


def upsert_rule(db: Session, merchant_key: str, category_id: str) -> MerchantRule:
    rule = db.scalar(select(MerchantRule).where(MerchantRule.merchant_key == merchant_key))
    if rule is None:
        rule = MerchantRule(merchant_key=merchant_key, category_id=category_id, source="user")
        db.add(rule)
    else:
        rule.category_id = category_id
    return rule


def reapply_rule(db: Session, rule: MerchantRule) -> int:
    """Re-run the brain on every statement holding unconfirmed rows for this merchant."""
    targets = db.scalars(
        select(Transaction).where(
            Transaction.merchant_key == rule.merchant_key,
            Transaction.status != TxnStatus.user_confirmed,
        )
    ).all()
    if not targets:
        return 0

    user_rules = learned_rules(db)
    target_ids = {txn.id for txn in targets}
    updated = 0
    for statement_id in sorted({txn.statement_id for txn in targets}):
        statement = db.get(Statement, statement_id)
        assert statement is not None
        txns = list(statement.transactions)
        by_row = {txn.row_index: txn for txn in txns}
        decisions = recategorize(txns, statement.account_type, user_rules)
        for txn, decision in zip(txns, decisions, strict=True):
            if txn.id not in target_ids:
                continue
            before = (txn.category_id, txn.status)
            apply_decision(txn, decision, by_row)
            updated += before != (txn.category_id, txn.status)
            rule.hits += rule_hit(decision) == rule.merchant_key
    return updated
