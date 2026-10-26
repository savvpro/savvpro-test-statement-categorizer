from app.brain.result import NEEDS_REVIEW, Decision
from app.brain.rules_loader import keyword_in


def check_keyword(txn, rules) -> Decision | None:
    hits = [r for r in rules["keyword_rules"] if keyword_in(txn.description, r["keyword"])]
    if not hits:
        return None
    rule = max(hits, key=lambda r: len(r["keyword"]))  # sab se lamba keyword jeetta hai
    kw = rule["keyword"]

    if txn.amount > 0:
        return Decision(
            NEEDS_REVIEW, "low",
            f"Money in from '{kw}' (an expense merchant); possible refund",
        )
    if rule.get("ambiguous"):
        return Decision(NEEDS_REVIEW, "low", rule.get("note", f"'{kw}' is ambiguous"))
    return Decision(rule["category"], "high", f"Matched keyword '{kw}'")