"""Description normalization.

Real statements are noisy: "UBER *TRIP HELP.UBER.COM 888-XXX", "SQ *JOES CAFE 9921",
"AMZN MKTPLACE PMTS". Before any rule fires we lowercase, strip punctuation and
drop long digit runs (merchant / authorization ids), then remove common card
noise terms. The same normalized text is what the user sees in the UI, so the
decision is always auditable.
"""

import re

_PUNCT = re.compile(r"[^a-z0-9&. ]+")
_LONG_DIGITS = re.compile(r"\b\d{3,}\b")
_MULTI_SPACE = re.compile(r"\s+")

# Terms card networks and banks inject into descriptions. Order matters for
# multi-word terms. Applied to the normalized string via plain substitution.
NOISE_TERMS = [
    "pos purchase",
    "card purchase",
    "recurring payment",
    "recurring pmt",
    "web srvce",
    "web payment",
    "debit card",
    "check card",
    "credit card",
    "purchase",
    "withdrawal",
    "recurring",
    "ppd id",
    "ach",
    "pmt",
    "pos",
]


def normalize(raw: str) -> str:
    """Light-touch normalization: case, punctuation, long digit runs.

    Kept conservative on purpose - special flows (transfers, refunds, income)
    are detected on this string, so words like "transfer" or "refund" survive.
    """
    s = (raw or "").lower().strip()
    s = _PUNCT.sub(" ", s)
    # Drop merchant ids / auth codes: "JOES CAFE 9921" -> "joes cafe",
    # "HELP.UBER.COM 888" -> the digits go, the domain text stays.
    s = _LONG_DIGITS.sub(" ", s)
    s = _MULTI_SPACE.sub(" ", s)
    return s.strip()


def strip_noise(norm: str) -> str:
    """Aggressive version used only for spending-keyword matching."""
    s = norm
    for term in NOISE_TERMS:
        s = re.sub(rf"\b{re.escape(term)}\b", " ", s)
    return _MULTI_SPACE.sub(" ", s).strip()
