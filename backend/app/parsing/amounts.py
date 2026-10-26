"""Amount strings -> Decimal. Never goes through float.

Assumptions (documented in DESIGN.md later):
- One currency per statement. "$", "€" and "£" are stripped, not converted.
- "." is the decimal separator and "," only groups thousands in threes, so "1,234.56" is
  accepted but an ambiguous "45,00" is rejected rather than guessed.
- Negative forms: "-45.00", "45.00-", "(45.00)" and the unicode minus sign (U+2212).
- A trailing "CR" makes the value positive (money in), "DR" negative (money out).
- An empty cell, or a lone "-" placeholder, means "no value" and returns None.
"""

import re
from decimal import Decimal

_MINUS_SIGNS = str.maketrans(dict.fromkeys("\u2212\u2012\u2013\u2014\ufe63\uff0d", "-"))
_NOISE = str.maketrans("", "", "$\u20ac\u00a3 \u00a0\u202f\u2009")
_MARKER_RE = re.compile(r"^(?P<body>.*[\d)])\s*(?P<marker>CR|DR)\.?$", re.IGNORECASE)
_NUMBER_RE = re.compile(r"^(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$|^\.\d+$")
_PLACEHOLDERS = {"-", "--"}


def parse_amount_with_marker(text: str) -> tuple[Decimal | None, str | None]:
    """Like `parse_amount`, but also returns the "CR"/"DR" marker if one was present."""
    value = text.strip().translate(_MINUS_SIGNS)
    if not value or value in _PLACEHOLDERS:
        return None, None

    marker = None
    if match := _MARKER_RE.match(value):
        value, marker = match["body"], match["marker"].upper()

    number = value.translate(_NOISE)
    signs = 0
    if number.startswith("(") and number.endswith(")"):
        number, signs = number[1:-1], signs + 1
    if number.endswith("-"):
        number, signs = number[:-1], signs + 1
    if number.startswith("-"):
        number, signs = number[1:], signs + 1
    elif number.startswith("+"):
        number = number[1:]

    if signs > 1 or (signs and marker) or not _NUMBER_RE.match(number):
        raise ValueError(f"invalid amount {text.strip()!r}")

    amount = Decimal(number.replace(",", ""))
    if marker == "DR" or signs:
        amount = -amount
    return amount, marker


def parse_amount(text: str) -> Decimal | None:
    return parse_amount_with_marker(text)[0]
