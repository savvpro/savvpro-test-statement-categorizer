"""Glue between DB rows and the pure brain: load learned rules, run it, write decisions back."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.brain.engine import categorize
from app.brain.models import AccountType, Decision, ParsedRow, TxnStatus
from app.db.models import MerchantRule, Transaction


def learned_rules(db: Session) -> dict[str, str]:
    return {rule.merchant_key: rule.category_id for rule in db.scalars(select(MerchantRule))}


def to_parsed_row(txn: Transaction) -> ParsedRow:
    return ParsedRow(
        row_index=txn.row_index,
        date=txn.date,
        description=txn.description_raw,
        amount=txn.amount,
        is_pending=txn.is_pending,
    )


def apply_decision(txn: Transaction, decision: Decision, by_row: dict[int, Transaction]) -> None:
    txn.merchant_key = decision.merchant_key
    txn.category_id = decision.category_id
    txn.suggested_category_id = decision.suggested_category_id
    txn.confidence = decision.confidence
    txn.status = decision.status
    txn.reasons = list(decision.reasons)
    txn.rule_id = decision.rule_id
    txn.flags = list(decision.flags)
    linked = (
        by_row.get(decision.linked_row_index) if decision.linked_row_index is not None else None
    )
    txn.linked_transaction = linked


def recategorize(
    txns: list[Transaction], account_type: AccountType, user_rules: dict[str, str]
) -> list[Decision]:
    """Run the brain over a whole statement so context signals (recurring, refunds) still work."""
    return categorize([to_parsed_row(txn) for txn in txns], account_type, user_rules)


def rule_hit(decision: Decision) -> str | None:
    """The learned rule's merchant key when that rule auto-assigned this row."""
    rule_id = decision.rule_id or ""
    if decision.status is TxnStatus.auto and rule_id.startswith("user:"):
        return rule_id.removeprefix("user:")
    return None


def count_rule_hits(db: Session, decisions: list[Decision]) -> None:
    keys = [key for d in decisions if (key := rule_hit(d))]
    if not keys:
        return
    for rule in db.scalars(select(MerchantRule).where(MerchantRule.merchant_key.in_(keys))):
        rule.hits += keys.count(rule.merchant_key)
