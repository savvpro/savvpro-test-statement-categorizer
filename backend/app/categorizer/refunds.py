from decimal import Decimal

from app.categorizer.context import Context
from app.categorizer.rulesdata import REFUNDKEYWORDS


def isrefundtxn(amount: Decimal, cleandesc: str, context: Context) -> bool:
    hasword = any(kw in cleandesc for kw in REFUNDKEYWORDS)
    role = context.counterparties.get(cleandesc, "")
    isexpense = amount < 0
    
    if isexpense:
        return hasword or role == "twoway"
    return hasword or role in ("twoway", "supplier")