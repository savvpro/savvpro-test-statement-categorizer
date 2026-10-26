from app.brain.result import TRANSFER, Decision
from app.brain.rules_loader import find_keyword


def check_transfer(txn, rules) -> Decision | None:
    kw = find_keyword(txn.description, rules["transfer_keywords"])
    if kw:
        return Decision(TRANSFER, "high", f"Matched transfer keyword '{kw}'")
    return None