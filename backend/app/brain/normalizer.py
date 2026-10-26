"""Raw statement description -> stable `merchant_key` used for lookups, rules and dedupe.

Regex only, deterministic. The raw description is kept separately for display and for
pattern rules that need the noisy text (e.g. "UBER *EATS" vs "UBER *TRIP").
"""

import re

# Payment processor / channel prefixes that hide the real merchant.
_PREFIX_RE = re.compile(
    r"^(?:SQ ?\*|TST ?\*|PAYPAL ?\*|PP ?\*|SP ?\*|GOOGLE ?\*|PY ?\*|POS |"
    r"DEBIT CARD PURCHASE |CARD PURCHASE |PURCHASE (?:AUTHORIZED )?(?:ON \d{1,2}/\d{1,2} )?)"
)
_MASKED_CARD_RE = re.compile(r"(?:X{2,}|\*{2,})\d{2,4}\b")
_PHONE_RE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")
_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
_HASH_NUMBER_RE = re.compile(r"#\s*\d+")
_DOMAIN_RE = re.compile(r"^([A-Z0-9-]+)(?:\.[A-Z0-9-]+)*\.(?:COM|NET|ORG|IO|CO|APP)(?:/\S*)?$")
_PUNCT_RE = re.compile(r"[^A-Z0-9&' ]+")

# Trailing "CITY ST". Two-letter codes that are also common words are left alone.
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CT", "FL", "GA", "IA", "ID", "IL", "KS", "KY", "LA",
    "MA", "MD", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV",
    "NY", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY", "DC",
}  # fmt: skip
_CITY_PREFIXES = {"SAN", "LOS", "LAS", "NEW", "SANTA", "ST", "FORT", "EL", "SALT"}


def _is_reference(token: str) -> bool:
    """Store numbers, payout and invoice references: anything mostly made of digits."""
    digits = sum(ch.isdigit() for ch in token)
    return digits > 0 and (token.isdigit() or (len(token) >= 5 and digits >= 2))


def _clean_domain(token: str, first: bool) -> str | None:
    match = _DOMAIN_RE.match(token)
    if not match:
        return token
    return match[1] if first else None  # "NETFLIX.COM" -> "NETFLIX"; "HELP.UBER.COM" dropped


def merchant_key(description: str) -> str:
    text = re.sub(r"\s+", " ", description.upper()).strip()
    previous = None
    while previous != text:  # prefixes can stack, e.g. "POS SQ *"
        previous, text = text, _PREFIX_RE.sub("", text).strip()

    for regex in (_MASKED_CARD_RE, _PHONE_RE, _DATE_RE, _HASH_NUMBER_RE):
        text = regex.sub(" ", text)

    tokens: list[str] = []
    for token in text.split():
        if _is_reference(token):
            continue
        cleaned = _clean_domain(token, first=not tokens)
        if cleaned:
            tokens.append(cleaned)

    words = _PUNCT_RE.sub(" ", " ".join(tokens)).split()
    words = [w for w in words if not w.isdigit()]
    if len(words) >= 3 and words[-1] in _US_STATES:
        words = words[:-2]
        if len(words) >= 2 and words[-1] in _CITY_PREFIXES:
            words = words[:-1]

    key = " ".join(words)
    return key or re.sub(r"\s+", " ", description.upper()).strip()
