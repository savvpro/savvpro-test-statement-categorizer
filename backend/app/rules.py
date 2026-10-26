"""The knowledge the brain uses: plain, reviewable keyword rules.

Each rule is (pattern, category, strength). Strength is how sure we are when the
pattern matches: 0.95 = an exact, well-known merchant; 0.7 = a generic word that
usually means this category. Patterns are matched against the normalised merchant.
"""
from __future__ import annotations

import re

from .models import Category as C

MerchantRule = tuple[re.Pattern[str], C, float]


def _r(pattern: str, category: C, strength: float) -> MerchantRule:
    return re.compile(pattern, re.I), category, strength


MERCHANT_RULES: list[MerchantRule] = [
    # Software & subscriptions used for design work
    _r(r"\badobe\b", C.SOFTWARE, 0.95),
    _r(r"\bfigma\b", C.SOFTWARE, 0.95),
    _r(r"\bcanva\b", C.SOFTWARE, 0.95),
    _r(r"\bdropbox\b", C.SOFTWARE, 0.9),
    _r(r"\bnotion\b", C.SOFTWARE, 0.9),
    _r(r"\bslack\b", C.SOFTWARE, 0.9),
    _r(r"\bgithub\b", C.SOFTWARE, 0.9),
    _r(r"\bwebflow\b", C.SOFTWARE, 0.95),
    _r(r"\bsquarespace\b", C.SOFTWARE, 0.9),
    _r(r"\bgoogle \*?(workspace|gsuite)\b", C.SOFTWARE, 0.95),
    _r(r"\b(shutterstock|envato|creative market)\b", C.SOFTWARE, 0.9),
    _r(r"\bzoom\.?us\b|\bzoom video\b", C.SOFTWARE, 0.9),
    # Advertising
    _r(r"\b(facebk|facebook|meta) ?ads\b|\bfacebk\b", C.ADVERTISING, 0.9),
    _r(r"\bgoogle \*?ads\b", C.ADVERTISING, 0.95),
    _r(r"\blinkedin\b", C.ADVERTISING, 0.75),
    _r(r"\bdribbble\b|\bbehance\b", C.ADVERTISING, 0.85),
    # Office
    _r(r"\b(staples|office depot|officemax)\b", C.OFFICE, 0.9),
    _r(r"\b(wacom|apple store|best buy|b&h photo)\b", C.OFFICE, 0.8),
    # Travel
    _r(r"\buber\b(?!.*eats)", C.TRAVEL, 0.85),
    _r(r"\blyft\b", C.TRAVEL, 0.9),
    _r(r"\b(delta|united|american) (air|airlines)\b|\bsouthwest\b|\bjetblue\b", C.TRAVEL, 0.9),
    _r(r"\b(marriott|hilton|hyatt|airbnb)\b", C.TRAVEL, 0.85),
    _r(r"\b(shell|chevron|exxon|bp)\b", C.TRAVEL, 0.65),
    _r(r"\bparking\b", C.TRAVEL, 0.75),
    # Meals
    _r(r"\b(starbucks|dunkin)\b", C.MEALS, 0.75),
    _r(r"\buber ?eats\b|\bdoordash\b|\bgrubhub\b", C.MEALS, 0.6),
    _r(r"\b(restaurant|grill|bistro|diner|pizzeria|sushi)\b", C.MEALS, 0.7),
    # Phone & internet
    _r(r"\b(verizon|t-mobile|tmobile|at&t|att\*?bill|comcast|xfinity|spectrum)\b", C.PHONE_INTERNET, 0.9),
    # Professional services
    _r(r"\b(legalzoom|quickbooks|intuit|turbotax|h&r block|freshbooks)\b", C.PROFESSIONAL, 0.9),
    _r(r"\b(cpa|accounting|attorney|law office)\b", C.PROFESSIONAL, 0.8),
    _r(r"\bupwork\b|\bfiverr\b", C.PROFESSIONAL, 0.7),
    # Education
    _r(r"\b(skillshare|udemy|coursera|domestika|masterclass)\b", C.EDUCATION, 0.9),
    # Fees
    _r(r"\b(annual fee|late fee|foreign transaction fee|interest charge|service fee|overdraft)\b", C.BANK_FEES, 0.95),
    # Clearly personal
    _r(r"\b(netflix|spotify|hulu|disney\+?|playstation|xbox|steam games)\b", C.PERSONAL, 0.85),
    _r(r"\b(whole foods|trader joe'?s|kroger|safeway|walmart grocery)\b", C.PERSONAL, 0.75),
    _r(r"\b(planet fitness|equinox|gym)\b", C.PERSONAL, 0.85),
]

# Merchants that sell both business and personal things. A match never auto-files;
# it always goes to review with a hint.
AMBIGUOUS_MERCHANTS = re.compile(r"\b(amazon|amzn|target|costco|walmart(?! grocery)|paypal|venmo|apple\.com/bill)\b", re.I)

TRANSFER = re.compile(r"\b(transfer|xfer|trnsfr|to savings|from savings|zelle to (self|own)|online banking transfer)\b", re.I)
CARD_PAYMENT = re.compile(r"\b(payment,? thank you|autopay payment|card payment|payment received|online payment)\b", re.I)
REFUND = re.compile(r"\b(refund|return|reversal|credit adj|chargeback|rfnd)\b", re.I)
CLIENT_INCOME = re.compile(r"\b(invoice|inv[ #-]?\d+|stripe transfer|stripe payout|client payment|ach credit|direct dep)\b", re.I)
P2P_INCOME = re.compile(r"\b(zelle from|venmo from|paypal transfer from)\b", re.I)
