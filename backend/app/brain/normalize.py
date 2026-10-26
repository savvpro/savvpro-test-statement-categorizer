"""Turn raw statement descriptions into a clean, comparable merchant string.

Bank descriptions are noisy. The same coffee shop can show up as::

    POS PURCHASE SQ *JOES CAFE 9921 SAN JOSE CA
    PURCHASE AUTHORIZED ON 03/12 SQ *JOES CAFE #9921 SAN JOSE CA CARD 4417

Both normalise to ``JOES CAFE SAN JOSE`` so that rules and the user's own corrections
apply to every variant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

US_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV "
    "NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
)

# Bank-added wrappers in front of the merchant name. Applied repeatedly from the left.
_BANK_PREFIXES = [
    re.compile(p)
    for p in (
        r"^PURCHASE AUTHORI[ZS]ED ON \d{1,2}/\d{1,2}\s+",
        r"^RECURRING (?:PAYMENT|DEBIT|PURCHASE)(?: AUTHORI[ZS]ED ON \d{1,2}/\d{1,2})?\s+",
        r"^(?:POS|DEBIT CARD|DBT CRD|CHECKCARD|CHECK CARD|VISA|CARD)"
        r"(?:\s+(?:PURCHASE|PUR|DEBIT|DBT|TRANSACTION|WITHDRAWAL))?\s*-?\s+",
        r"^(?:\d{2}/\d{2}|\d{4})\s+",  # transaction date the bank glued on (MM/DD or MMDD)
    )
]

# Payment processors that sit between the bank and the real merchant. GOOGLE * and
# APPLE are left alone on purpose: "GOOGLE *FI" is the merchant (a phone plan).
_PROCESSOR_PREFIX = re.compile(r"^(?:SQ|TST|PP|PAYPAL|PY|IN|SP|FS|BT|CKO)\s?\*\s*")

_NOISE = [
    re.compile(p)
    for p in (
        r"\bCARD\s*(?:ENDING(?: IN)?\s*)?[X*]*\d{4}\b",  # card last-4
        r"\b(?:PPD|CCD|CTX)\b(?:\s*ID\s*:?\s*\d*)?|\b(?:WEB|TEL)\s+ID\s*:?\s*\d+",  # ACH codes
        r"\b(?:REF(?:ERENCE)?|ID|CONF|TRACE|TRN|AUTH)(?:\s*(?:NUMBER|NO|NBR))?\s*[#:.]?\s*"
        r"(?=[A-Z0-9]*\d)[A-Z0-9]{4,}\b",  # reference numbers
        r"\b\d{3}[-.]\d{3}[-.]\d{4}\b",  # phone numbers
        r"\b(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{6,}\b",  # mixed ids like 2K4LM19QX
        r"\b[X*]{2,}\d+\b",  # masked account numbers XXXXXX1234
        r"#\s*\d+",  # store numbers
        r"\b\d{3,}\b",  # long digit runs (store ids, dates) - keeps short brand numbers like 76
    )
]

_PUNCT = re.compile(r"[*#|_~]+")
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Normalized:
    raw: str
    text: str  # cleaned, upper-case text used for rule matching
    key: str  # stable lookup key for learned user rules


def _strip_prefixes(text: str) -> str:
    changed = True
    while changed:
        changed = False
        for pattern in _BANK_PREFIXES:
            new = pattern.sub("", text, count=1)
            if new != text:
                text, changed = new, True
    return _PROCESSOR_PREFIX.sub("", text, count=1)


def _strip_trailing_state(text: str) -> str:
    words = text.split(" ")
    if len(words) > 2 and words[-1] in US_STATES:
        words = words[:-1]
    return " ".join(words)


def normalize(raw: str) -> Normalized:
    text = _SPACES.sub(" ", (raw or "").upper()).strip()
    text = _strip_prefixes(text)
    for pattern in _NOISE:
        text = pattern.sub(" ", text)
    text = _PUNCT.sub(" ", text)
    text = _SPACES.sub(" ", text).strip(" -.,/")
    text = _strip_trailing_state(text)
    if not text:  # description was nothing but noise - fall back to the raw value
        text = _SPACES.sub(" ", (raw or "").upper()).strip()
    key = _SPACES.sub(" ", re.sub(r"[^A-Z0-9 ]", " ", text)).strip().lower()
    return Normalized(raw=raw, text=text, key=key)
