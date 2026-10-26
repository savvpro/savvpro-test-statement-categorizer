from app.brain.result import NEEDS_REVIEW, Decision
from app.config import BASE_CURRENCY


def check_currency(txn, rules) -> Decision | None:
    if txn.currency != BASE_CURRENCY:
        return Decision(
            NEEDS_REVIEW,
            "low",
            f"Foreign currency ({txn.currency}); amount not converted to {BASE_CURRENCY}",
        )
    return None