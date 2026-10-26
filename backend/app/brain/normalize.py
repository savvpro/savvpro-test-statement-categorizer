"""Turn a messy bank description into a clean, comparable string.

'ELECTRIC CO *AUTOPAY'      -> 'ELECTRIC CO'
'ACE PLUMBING 4412'         -> 'ACE PLUMBING'
'TRANSFER TO SAVINGS ****1234' -> 'TRANSFER TO SAVINGS'
"""
import re

# Words banks add that say nothing about what the transaction is.
NOISE_WORDS = frozenset(
    {"POS", "PURCHASE", "DEBIT", "CARD", "CHECKCARD", "RECURRING",
     "AUTOPAY", "ACH", "WEB", "ONLINE"}
)

_MASKED_ACCOUNT = re.compile(r"[X*#]{2,}\s*\d+")       # ****1234, XXXX1234
_SHORT_DATE = re.compile(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b")  # 03/04, 03/04/25
_NON_ALNUM = re.compile(r"[^A-Z0-9 ]+")
_LONG_NUMBER = re.compile(r"\b\d{3,}\b")               # store / check numbers


def normalize(description: str) -> str:
    text = description.upper()
    text = _MASKED_ACCOUNT.sub(" ", text)
    text = _SHORT_DATE.sub(" ", text)
    text = _NON_ALNUM.sub(" ", text)
    text = _LONG_NUMBER.sub(" ", text)
    words = [w for w in text.split() if w not in NOISE_WORDS]
    return " ".join(words)