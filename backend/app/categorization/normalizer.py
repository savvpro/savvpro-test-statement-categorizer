"""Turns noisy bank descriptions into stable text and merchant keys."""
import re

_PREFIXES = re.compile(
    r"^(CARD PAYMENT TO|CARD PURCHASE|CONTACTLESS|POS|VIS|VISA|DD|SO|BGC|FPI|FPO|DEB)\s+"
)
_NOISE = re.compile(r"\b(\d{4,}|\d{1,2}[/.-]\d{1,2}([/.-]\d{2,4})?|ON \d{1,2} \w{3})\b")
_MERCHANT_STOPWORDS = frozenset({
    "LTD", "LIMITED", "INC", "PLC", "LLC", "COM", "CO", "UK", "GB", "PMTS", "MKTPLACE",
    "WWW", "ONLINE", "REFUND", "REVERSAL", "RETURN",
})


def normalize(description: str) -> str:
    """'CARD PAYMENT TO UBER *TRIP 8812 ON 03 MAR' -> 'UBER TRIP'."""
    text = re.sub(r"[^A-Z0-9/.\- ]", " ", description.upper())
    text = _PREFIXES.sub("", " ".join(text.split()))
    text = _NOISE.sub(" ", text)
    text = re.sub(r"[/.\-]", " ", text)
    return " ".join(text.split())


def merchant_key(normalized: str) -> str:
    """Stable merchant identity: 'TRAINLINE COM REFUND' and 'TRAINLINE COM' -> 'TRAINLINE'."""
    words = [w for w in normalized.split() if w not in _MERCHANT_STOPWORDS and not w.isdigit()]
    return " ".join(words[:2]) or normalized
