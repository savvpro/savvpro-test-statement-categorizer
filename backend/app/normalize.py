"""Turns raw bank text like 'SQ *JOES CAFE 9921 SEATTLE' into stable forms.

`clean` keeps every word (used for rule matching).
`merchant_key` keeps only the identifying words (used to group the same
merchant and to remember the user's corrections).
"""

import re

_NON_ALNUM = re.compile(r"[^A-Z0-9]+")

# Payment-processor / terminal prefixes that say nothing about the merchant.
_PREFIXES = {"SQ", "TST", "SP", "POS", "DEBIT", "PURCHASE", "CHECKCARD", "RECURRING", "VISA", "CARD", "ONLINE"}
_STOPWORDS = {"THE", "A", "AN", "OF"}
_KEY_WORDS = 2


def clean(description: str) -> str:
    return _NON_ALNUM.sub(" ", description.upper()).strip()


def merchant_key(description: str) -> str:
    words = [
        word
        for word in clean(description).split()
        if word not in _PREFIXES and word not in _STOPWORDS and not any(char.isdigit() for char in word)
    ]
    return " ".join(words[:_KEY_WORDS]) or clean(description)
