"""Turn a raw statement description into a clean merchant name.

"SQ *JOES CAFE 9921"      -> "JOES CAFE"
"PAYPAL *ADOBE"           -> "ADOBE"
"UBER *TRIP 8812"         -> "UBER TRIP"
"HOTEL LISBOA EUR 120.00" -> "HOTEL LISBOA"  (+ foreign amount 120.00 EUR)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Payment processors / terminals that put their own name in front of the merchant.
PROCESSOR_PREFIXES = (
    "SQ *",
    "SQ*",
    "PAYPAL *",
    "PAYPAL*",
    "PP*",
    "TST*",
    "TST *",
    "SP *",
    "SP*",
    "IZ *",
    "IZ*",
    "POS ",
    "CHECKCARD ",
    "DEBIT CARD PURCHASE ",
    "PURCHASE ",
)

FOREIGN_AMOUNT = re.compile(r"\b(USD|EUR|GBP|PKR|CAD|AUD|INR|AED|JPY|CHF)\s*([\d,]+\.\d{2})\b")
# Long numbers (store / reference ids) and letter-digit codes with 2+ digits (2K4L1).
REFERENCE_TOKEN = re.compile(r"^#?\d{4,}$|^(?=(?:.*\d){2})[A-Z0-9]{5,}$|^#\d+$")


@dataclass(frozen=True)
class Normalized:
    merchant: str
    foreign_currency: str | None = None
    foreign_amount: float | None = None


def normalize(description: str) -> Normalized:
    text = " ".join(description.upper().split())

    currency = amount = None
    match = FOREIGN_AMOUNT.search(text)
    if match:
        currency = match.group(1)
        amount = float(match.group(2).replace(",", ""))
        text = (text[: match.start()] + text[match.end() :]).strip()

    stripped = True
    while stripped:  # prefixes can be stacked, e.g. "POS SQ *..."
        stripped = False
        for prefix in PROCESSOR_PREFIXES:
            if text.startswith(prefix) and len(text) > len(prefix):
                text = text[len(prefix) :].strip()
                stripped = True

    text = re.sub(r"[^A-Z0-9& ]+", " ", text)
    tokens = [token for token in text.split() if not REFERENCE_TOKEN.match(token)]
    merchant = " ".join(tokens) or " ".join(text.split())
    return Normalized(merchant=merchant, foreign_currency=currency, foreign_amount=amount)
