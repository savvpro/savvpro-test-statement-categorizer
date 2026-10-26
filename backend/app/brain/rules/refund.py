# backend/app/brain/rules/refund.py
import re
from ..models import Transaction, Decision, Category

_REFUND = re.compile(r"\b(REFUND|RETURN|REVERSAL|CHARGEBACK|CREDIT)\b")

def match(tx: Transaction) -> Decision | None:
    if tx.amount > 0 and _REFUND.search(tx.normalized):
        return Decision(Category.REFUND, 0.95,
                        f"Refund keyword on inbound amount ({tx.normalized})")
    if tx.amount < 0 and _REFUND.search(tx.normalized):
        # e.g. "REFUND TO CUSTOMER" — money going out as a refund
        return Decision(Category.REFUND, 0.90,
                        f"Outbound refund ({tx.normalized})")
    return None