"""Stage 1: transfers, card payments, owner moves, interest, bank fees, returned items."""

from app.brain import explain
from app.brain.rules import RuleSet
from app.brain.state import RowState

SHORT_CIRCUIT_SCORE = 0.97


def apply(state: RowState, rules: RuleSet) -> None:
    txn = state.txn
    for rule in rules.structural:
        if txn.direction not in rule.directions or txn.account_type not in rule.account_types:
            continue
        if not rule.pattern.search(state.text):
            continue
        state.add(
            rule.category, rule.score, "structural", rule.id, explain.structural(rule.category)
        )
        state.flags |= rule.flags
        if rule.is_refund:
            state.is_refund = True
        if rule.score >= SHORT_CIRCUIT_SCORE:
            state.short_circuit = True
