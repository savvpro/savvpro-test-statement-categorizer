"""Turns a messy bank description into a stable merchant key.

'FOODPANDA*ORDER 77812' -> 'FOODPANDA ORDER'
'shell petrol stn #4421 Lahore' -> 'SHELL PETROL STN'

The same key is used for matching rules and for remembering what the user taught us,
so 'ALI TRADERS 5521' and 'ALI TRADERS 7733' are the same merchant.
"""

import re
import unicodedata

_DATE_TOKEN = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?\b")
_SEPARATORS = re.compile(r"[\W_]+")  # unicode-aware: keeps letters from any script


def _is_reference(token: str) -> bool:
    """Branch/store numbers, order ids, terminal ids: noise that changes on every transaction.

    A bare number is dropped ('STN 9', '#4421'); mixed tokens such as 'M2' or '4G' are
    real words and stay, unless they carry a long id ('TXN12345').
    """
    digits = sum(ch.isdigit() for ch in token)
    return token.isdigit() or digits >= 4


def normalize(description: str, noise: re.Pattern[str] | None = None) -> str:
    text = unicodedata.normalize("NFKC", description).upper()
    text = _DATE_TOKEN.sub(" ", text)
    text = _SEPARATORS.sub(" ", text)
    text = " ".join(t for t in text.split() if not _is_reference(t))
    if noise is not None:
        text = noise.sub(" ", text)
    return " ".join(text.split())
