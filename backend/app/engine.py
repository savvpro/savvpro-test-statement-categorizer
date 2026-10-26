import re
from collections.abc import Callable

from .passes import apply_passes
from .rules import RULES, Rule
from .schemas import NEEDS_REVIEW, Transaction

MATCHERS: dict[str, Callable[[str, str], bool]] = {
    "exact": lambda pattern, text: text == pattern,
    "keyword": lambda pattern, text: (
        re.search(rf"(?<![A-Z0-9]){re.escape(pattern)}(?![A-Z0-9])", text) is not None
    ),
    "regex": lambda pattern, text: re.search(pattern, text) is not None,
}


def applies(rule: Rule, tx: Transaction) -> bool:
    direction = "credit" if tx.amount > 0 else "debit"
    if rule.direction and rule.direction != direction:
        return False
    if rule.usd_only and not tx.usd_hint:
        return False
    return MATCHERS[rule.kind](rule.pattern, tx.normalized)


def categorize(tx: Transaction) -> None:
    tx.flags = []
    tx.refund_of = None
    for rule in RULES:
        if applies(rule, tx):
            tx.assign(rule.category, rule.confidence, rule.reason)
            return
    tx.assign(NEEDS_REVIEW, 0.0, "No rule matched: unknown merchant")


def categorize_all(transactions: list[Transaction]) -> list[Transaction]:
    for tx in transactions:
        categorize(tx)
    apply_passes(transactions)
    return transactions
