"""
Stage 0 – Normalize raw descriptions into a clean merchant_key.

Pure function: no DB, no side effects.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date


@dataclass
class NormalizedRow:
    """Output of normalization – input to brain stages."""
    row_index: int
    posted_date: date
    raw_description: str
    merchant_key: str
    amount_cents: int            # negative = debit, positive = credit
    currency: str = "USD"
    fingerprint: str = ""


# ── Processor prefixes ──────────────────────────────────────────────────────
# Pattern → replacement.  We strip the prefix and keep the merchant name.
_PROCESSOR_PREFIXES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^SQ\s*\*\s*", re.I), ""),
    (re.compile(r"^TST\s*\*\s*", re.I), ""),
    (re.compile(r"^PAYPAL\s*\*\s*", re.I), ""),
    (re.compile(r"^GOOGLE\s*\*\s*", re.I), "GOOGLE "),
    (re.compile(r"^APPLE\.COM/", re.I), "APPLE "),
    (re.compile(r"^AMZN\s+MKTP(\s+US)?\b.*", re.I), "AMAZON"),
    (re.compile(r"^AMAZON\.COM\b.*", re.I), "AMAZON"),
    (re.compile(r"^AMZN\b\s*", re.I), "AMAZON"),
    (re.compile(r"^SP\s+", re.I), ""),            # Shopify
    (re.compile(r"^CKO\s*\*\s*", re.I), ""),       # Checkout.com
]

# ── Noise tokens to strip ───────────────────────────────────────────────────
_NOISE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bPOS\b", re.I),
    re.compile(r"\bDEBIT\s*CARD\s*PURCHASE\b", re.I),
    re.compile(r"\bCHECKCARD\b", re.I),
    re.compile(r"\bPURCHASE\b", re.I),
    re.compile(r"\bWITHDRAWAL\b", re.I),
    re.compile(r"\bPENDING\b", re.I),
    # Trailing store numbers  (#1234, 1234)
    re.compile(r"#\d{2,}"),
    re.compile(r"\b\d{4,}\b"),
    # Trailing dates  01/15, 01/15/26
    re.compile(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b"),
    # City/State at end  "NEW YORK NY", "SAN FRANCISCO CA 94105"
    re.compile(r"\b[A-Z]{2}\s*\d{5}(-\d{4})?\s*$"),
    re.compile(r"\b[A-Z][a-z]+\s+[A-Z]{2}\s*$"),
    # Asterisk separators
    re.compile(r"\*"),
    # Extra whitespace (collapsed after everything else)
    re.compile(r"\s{2,}"),
]


def normalize_description(raw: str) -> str:
    """Clean a raw transaction description and return a merchant_key."""
    text = raw.upper().strip()

    # Strip processor prefixes
    for pat, repl in _PROCESSOR_PREFIXES:
        text = pat.sub(repl, text)

    # Strip noise
    for pat in _NOISE_PATTERNS:
        text = pat.sub(" ", text)

    text = text.strip()
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text


def compute_fingerprint(posted_date: date, raw_description: str, amount_cents: int) -> str:
    """
    SHA-256 based fingerprint for duplicate detection.
    Same date + description + amount → same fingerprint.
    """
    payload = f"{posted_date.isoformat()}|{raw_description.strip().upper()}|{amount_cents}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def parse_amount_cents(
    value: str | None,
    *,
    debit_value: str | None = None,
    credit_value: str | None = None,
    account_type: str = "credit_card",
) -> int:
    """
    Convert a dollar string to integer cents.

    Handles:
     - Single signed column ("value")
     - Separate debit/credit columns
     - Parenthesized negatives: (123.45) → -12345
     - Dr/Cr marker in the string

    Returns negative for debits (money out), positive for credits (money in).
    """
    if debit_value is not None or credit_value is not None:
        debit_cents = _str_to_cents(debit_value) if debit_value else 0
        credit_cents = _str_to_cents(credit_value) if credit_value else 0
        # Debit column values are usually positive numbers meaning money out
        return credit_cents - debit_cents

    if value is None:
        return 0

    text = value.strip()
    if not text or text == "--":
        return 0

    # Parenthesized negative: (123.45)
    if text.startswith("(") and text.endswith(")"):
        return -abs(_str_to_cents(text[1:-1]))

    # Dr/Cr marker
    is_debit = False
    for marker in (" DR", " DR.", " DB"):
        if text.upper().endswith(marker):
            text = text[: -len(marker)].strip()
            is_debit = True
            break
    for marker in (" CR", " CR."):
        if text.upper().endswith(marker):
            text = text[: -len(marker)].strip()
            # explicit credit
            break

    cents = _str_to_cents(text)

    if is_debit:
        return -abs(cents)

    # For credit cards, a positive amount is typically a charge (debit).
    # But many banks export charges as negative already.
    # We keep the sign as-is from the file; the caller can invert via account_type.
    return cents


def _str_to_cents(s: str | None) -> int:
    """Parse a numeric string to integer cents.  '$1,234.56' → 123456."""
    if not s:
        return 0
    cleaned = s.replace("$", "").replace(",", "").strip()
    if not cleaned or cleaned == "-":
        return 0
    # Handle negative sign
    negative = cleaned.startswith("-")
    if negative:
        cleaned = cleaned[1:]
    # Split on decimal point
    parts = cleaned.split(".")
    if len(parts) == 1:
        cents = int(parts[0]) * 100
    elif len(parts) == 2:
        dollars = int(parts[0]) if parts[0] else 0
        frac = parts[1].ljust(2, "0")[:2]  # exactly 2 decimal digits
        cents = dollars * 100 + int(frac)
    else:
        raise ValueError(f"Cannot parse amount: {s!r}")
    return -cents if negative else cents
