from app.brain.result import INCOME, Decision
from app.brain.rules_loader import find_keyword


def check_income(txn, rules) -> Decision | None:
    if txn.amount <= 0:
        return None
    kw = find_keyword(txn.description, rules["income_keywords"])
    if kw:
        return Decision(INCOME, "high", f"Money in + '{kw}'")
    return None