from app.brain.checks import CHECKS
from app.brain.checks.duplicate import duplicate_key
from app.brain.result import DUPLICATE_IGNORE, NEEDS_REVIEW, TRANSFER, Decision
from app.brain.rules_loader import load_rules
from app.schemas import Transaction


def decide(txn: Transaction, rules: dict) -> Decision:
    for check in CHECKS:
        decision = check(txn, rules)
        if decision:
            return decision
    if txn.amount > 0:
        return Decision(NEEDS_REVIEW, "low", "Money in from an unknown source")
    return Decision(NEEDS_REVIEW, "low", "No matching rule")


def categorize(transactions: list[Transaction], rules: dict | None = None) -> list[Transaction]:
    """Har row ko category deta hai (rows ko in-place update karta hai)."""
    rules = rules or load_rules()
    seen: dict[tuple, int] = {}

    for txn in transactions:
        decision = decide(txn, rules)
        key = duplicate_key(txn)

        if key in seen and decision.category != TRANSFER:
            # Chup chaap hatana nahi, user se poochna hai
            decision = Decision(
                NEEDS_REVIEW,
                "low",
                f"Possible duplicate of row {seen[key]} (would otherwise be "
                f"'{decision.category}'). Confirm, or mark as '{DUPLICATE_IGNORE}'.",
            )
        else:
            seen.setdefault(key, txn.row)

        txn.category = decision.category
        txn.confidence = decision.confidence
        txn.reason = decision.reason
        txn.tax_deductible = rules["categories"].get(decision.category, "unknown")

    return transactions