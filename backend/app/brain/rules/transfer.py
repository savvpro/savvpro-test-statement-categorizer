# backend/app/brain/rules/transfer.py
import re
from ..models import Transaction, Decision, Category

_TRANSFER = re.compile(
    r"\b(TRANSFER|AUTOPAY|PAYMENT TO CARD|ONLINE TRANSFER|SAVINGS|"
    r"BANK TO BANK|WIRE TO SELF)\b"
)

def match(tx: Transaction) -> Decision | None:
    if _TRANSFER.search(tx.normalized):
        return Decision(Category.NOT_SPENDING, 0.90,
                        f"Transfer/autopay pattern ({tx.normalized})")
    return None