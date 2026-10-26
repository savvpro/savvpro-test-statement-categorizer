# backend/app/brain/rules/income.py
import re
from ..models import Transaction, Decision, Category

_PAYOUT = re.compile(r"\b(SHOPIFY PAYOUT|ETSY DEPOSIT|STRIPE PAYOUT|PAYPAL TRANSFER IN)\b")

def match(tx: Transaction) -> Decision | None:
    if tx.amount > 0 and _PAYOUT.search(tx.normalized):
        return Decision(Category.INCOME, 0.92,
                        f"Marketplace payout ({tx.normalized})")
    return None