from app.brain.result import NEEDS_REVIEW, REFUND, Decision
from app.brain.rules_loader import find_keyword


def check_refund(txn, rules) -> Decision | None:
    kw = find_keyword(txn.description, rules["refund_keywords"])
    if not kw:
        return None
    if txn.amount > 0:
        return Decision(REFUND, "high", f"Money in + '{kw}': refund, not income")
    # REFUND lafz hai magar paisa gaya hai (maslan customer ko refund)
    return Decision(
        NEEDS_REVIEW, "low", f"'{kw}' found but money went out; unclear what this is"
    )