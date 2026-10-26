# backend/app/brain/rules/merchants.py
import re
from ..models import Transaction, Decision, Category

# (pattern, category, confidence, label)
_RULES = [
    (r"\bSHOPIFY\b",            Category.PLATFORM_FEES, 0.90, "Shopify"),
    (r"\bETSY\b",               Category.PLATFORM_FEES, 0.90, "Etsy fees"),
    (r"\bSTRIPE\b",             Category.PLATFORM_FEES, 0.85, "Stripe fees"),
    (r"\bUSPS\b|\bUPS\b|\bFEDEX\b", Category.SHIPPING,  0.92, "Carrier"),
    (r"\bALIBABA\b|\bSUPPLIER\b|\bWHOLESALE\b",
                                Category.INVENTORY,     0.85, "Supplier"),
    (r"\bFACEBOOK ADS\b|\bMETA ADS\b|\bGOOGLE ADS\b|\bINSTAGRAM\b",
                                Category.MARKETING,     0.90, "Ads"),
    (r"\bCANVA\b|\bMAILCHIMP\b|\bGOOGLE WORKSPACE\b",
                                Category.SOFTWARE,      0.88, "SaaS"),
]

_COMPILED = [(re.compile(p), c, conf, label) for p, c, conf, label in _RULES]

def match(tx: Transaction) -> Decision | None:
    for pat, cat, conf, label in _COMPILED:
        if pat.search(tx.normalized):
            return Decision(cat, conf, f"{label} match ({tx.normalized})")
    return None