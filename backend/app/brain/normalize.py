"""Turn a raw statement description into a stable merchant key.

`SQ *JOES CAFE 9921 SAN JOSE CA` and `JOES CAFE #0042` should both end up as `JOES CAFE`,
so that rules, refund matching and "apply to similar" all see the same thing.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Payment-processor and point-of-sale prefixes that say nothing about the merchant.
_PROCESSOR_PREFIX = re.compile(
    r"^(?:SQ|TST|SP|PP|PAYPAL|STRIPE|CKO|POS|PURCHASE|DEBIT CARD PURCHASE|CHECKCARD|"
    r"VISA PURCHASE|CARD PURCHASE|RECURRING PAYMENT|RECURRING|ONLINE PAYMENT TO|"
    r"POS DEBIT|DDA PURCHASE|EXT CREDIT CARD)(?:\s*[*:\-]\s*|\s+)",
)
_WORD_THEN_NUMBER = re.compile(r"^([A-Z]{2,})(\d{4,})$")
_STAR_SPLIT = re.compile(r"\s*\*\s*")
_MASKED_CARD = re.compile(r"\b(?:X{2,}|\*{2,})\d{2,4}\b")
_URL_PREFIX = re.compile(r"\b(?:HTTPS?://)?WWW\.")
_DOMAIN_SUFFIX = re.compile(r"\.(?:COM|NET|ORG|IO|CO|AI|APP|DEV)(?:/[A-Z0-9/_-]*)?\b")
_PLACE_CODES = frozenset(
    {
        *("US", "USA", "GB", "UK", "CA", "NY", "TX", "FL", "WA", "IL", "MA", "PA", "OH"),
        *("GA", "NC", "VA", "NJ", "MI", "AZ", "CO", "OR", "CT", "MD", "MN", "TN"),
    }
)
_REFERENCE_TOKEN = re.compile(r"^(?:#?\d[\dA-Z]*\d|#\w+|\d)$")
# Order or auth codes such as DQ6HO9775: long, with letters and at least three digits.
_MIXED_REFERENCE = re.compile(r"^(?=.*[A-Z])(?=(?:.*\d){3,})[A-Z0-9]{6,}$")
_NOISE_WORDS = {
    "THE",
    "INC",
    "LLC",
    "LTD",
    "CORP",
    "CO",
    "PAYMENT",
    "PMT",
    "POS",
    "PURCHASE",
    "AUTH",
}


@dataclass(frozen=True)
class Normalized:
    text: str  # cleaned description, all tokens kept
    key: str  # short stable merchant key, used for learning and refund matching
    tokens: tuple[str, ...]  # brand words only, reference numbers removed
    all_tokens: tuple[str, ...]  # every token, used for phrase matching ("OFFICE 365")


def _strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def normalize(description: str) -> Normalized:
    text = _strip_accents(description).upper().replace("'", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = _MASKED_CARD.sub(" ", text)

    # "SQ *JOES CAFE" -> "JOES CAFE"; "AMZN MKTP US*2K4" -> "AMZN MKTP US 2K4"
    for _ in range(2):
        stripped = _PROCESSOR_PREFIX.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped
    text = _STAR_SPLIT.sub(" ", text)
    text = _URL_PREFIX.sub("", text)
    text = _DOMAIN_SUFFIX.sub(" ", text)
    text = re.sub(r"[^A-Z0-9&#'/ ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    raw_tokens: list[str] = []
    for token in text.split():
        glued = _WORD_THEN_NUMBER.match(token)  # "ADS3847261" -> "ADS", "3847261"
        raw_tokens.extend(glued.groups() if glued else [token])

    # Drop reference numbers and store numbers, then the city/state/country tail.
    tokens = [
        t for t in raw_tokens if not (_REFERENCE_TOKEN.match(t) or _MIXED_REFERENCE.match(t))
    ] or list(raw_tokens)
    while len(tokens) > 1 and tokens[-1] in _PLACE_CODES:
        tokens.pop()

    key_tokens = [t for t in tokens if t not in _NOISE_WORDS][:4] or tokens[:4]
    return Normalized(
        text=" ".join(tokens),
        key=" ".join(key_tokens),
        tokens=tuple(tokens),
        all_tokens=tuple(raw_tokens),
    )
