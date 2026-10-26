"""Merchant name normalization – strips processor noise, extracts clean name."""
from __future__ import annotations

import re

# ── Prefix patterns (strip in order, first match wins) ─────────────────────────
_PREFIX_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^SQ\s*\*\s*", re.I),
    re.compile(r"^TST\s*\*\s*", re.I),
    re.compile(r"^PAYPAL\s*\*\s*", re.I),
    re.compile(r"^VENMO\s*\*\s*", re.I),
    re.compile(r"^STRIPE\s*\*\s*", re.I),
    re.compile(r"^POS DEBIT\s*", re.I),
    re.compile(r"^DEBIT CARD PURCHASE\s*", re.I),
    re.compile(r"^CHECKCARD\s+\d{4}\s*", re.I),
    re.compile(r"^ACH DEBIT\s+", re.I),
    re.compile(r"^ACH CREDIT\s+", re.I),
    re.compile(r"^ACH\s+", re.I),
    re.compile(r"^ONLINE PURCHASE\s+", re.I),
    re.compile(r"^PURCHASE\s+AUTHORIZED\s+", re.I),
    re.compile(r"^RECURRING PURCHASE\s+", re.I),
    re.compile(r"^CARD PURCHASE\s+", re.I),
    re.compile(r"^DIRECT DEBIT\s+", re.I),
    re.compile(r"^WEB PAYMENT\s+", re.I),
    re.compile(r"^BILL PAYMENT\s+", re.I),
]

_STATE_CODES = (
    "AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|"
    "MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|"
    "WV|WI|WY|DC"
)

# ── Suffix patterns (applied iteratively until stable) ─────────────────────────
_SUFFIX_PATTERNS: list[re.Pattern[str]] = [
    # URLs – must run first
    re.compile(r"\s+https?://\S+", re.I),
    re.compile(r"\s+\S+\.(COM|NET|ORG|IO|CO|APP|DEV|AI)\S*", re.I),
    # Phone number
    re.compile(r"\s+\d{3}[-.]?\d{3}[-.]?\d{4}$"),
    # "NUMBER CITY STATE" at end – store number followed by city+state
    # e.g. "9921 BROOKLYN NY", "1234 AUSTIN TX"
    re.compile(
        rf"\s+\d{{1,6}}\s+[A-Z]{{2,}}(?:\s+[A-Z]{{2,}})?\s+(?:{_STATE_CODES})\s*$"
    ),
    # Standalone trailing state code – strip just the 2-letter state
    re.compile(rf"\s+(?:{_STATE_CODES})\s*$"),
    # Store # / ref codes
    re.compile(r"\s+#\w+$"),
    re.compile(r"\s+\d{4,}$"),                 # trailing long number (≥4 digits)
    # Date/time stamps
    re.compile(r"\s+\d{2}/\d{2}(?:/\d{2,4})?$"),
    re.compile(r"\s+ON\s+\d{2}/\d{2}", re.I),
    # *WORD suffix (e.g. UBER *TRIP → UBER) – runs last
    re.compile(r"\s*\*\w+$"),
]

_WS = re.compile(r"\s{2,}")


def normalize_merchant(raw: str) -> str:
    """Return a cleaned-up merchant name from a raw bank description."""
    text = raw.upper().strip()

    # Strip prefixes (first match only)
    for pat in _PREFIX_PATTERNS:
        new = pat.sub("", text)
        if new != text:
            text = new.strip()
            break  # one prefix at a time (re-entry via outer loop if needed)

    # Strip suffixes iteratively until stable
    prev = None
    while prev != text:
        prev = text
        for pat in _SUFFIX_PATTERNS:
            text = pat.sub("", text).strip()

    # Collapse internal whitespace
    text = _WS.sub(" ", text).strip()

    return text or raw.upper().strip()
