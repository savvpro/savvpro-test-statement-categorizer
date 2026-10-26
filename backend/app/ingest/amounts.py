"""Amount parsing – handles all real-world bank formats and sign conventions."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_PAREN_RE = re.compile(r"^\(([0-9,. ]+)\)$")      # (12.00) → negative
_TRAILING_MINUS_RE = re.compile(r"^([0-9,. ]+)-$") # 12.00- → negative
_CR_DR_RE = re.compile(r"^([0-9,. ]+)\s*(CR|DR)$", re.I)
_CURRENCY_CLEAN_RE = re.compile(r"[£€¥₹$,\s]")


def parse_amount(value: str) -> int:
    """Parse any bank amount string to signed integer cents.

    Negative = outflow (debit/spend).
    Positive = inflow (credit/deposit).

    Raises ValueError for blanks/non-numeric.
    """
    value = value.strip()
    if not value:
        raise ValueError("Empty amount")

    is_negative = False

    # Leading minus
    if value.startswith("-"):
        is_negative = True
        value = value[1:]

    # Strip currency symbols before paren check (handles ($12.34))
    value_stripped = _CURRENCY_CLEAN_RE.sub("", value)

    # (12.00) → negative; also handles ($12.34) after currency strip
    m = _PAREN_RE.match(value) or _PAREN_RE.match(value_stripped)
    if m:
        is_negative = True
        value = m.group(1)

    # 12.00- → negative
    m = _TRAILING_MINUS_RE.match(value)
    if m:
        is_negative = True
        value = m.group(1)

    # 12.00 CR / 12.00 DR
    m = _CR_DR_RE.match(value)
    if m:
        amount_str = m.group(1)
        suffix = m.group(2).upper()
        if suffix == "DR":
            is_negative = True
        value = amount_str

    # Strip currency symbols and commas
    value = _CURRENCY_CLEAN_RE.sub("", value)

    try:
        dec = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"Cannot parse amount: {value!r}") from None

    cents = int(dec * 100)
    return -cents if is_negative else cents


def parse_debit_credit(debit_str: str, credit_str: str) -> int:
    """Handle split debit/credit columns.

    Debit column (money out) → negative cents.
    Credit column (money in) → positive cents.
    """
    debit_str = debit_str.strip()
    credit_str = credit_str.strip()

    if credit_str and not debit_str:
        return parse_amount(credit_str)  # positive
    if debit_str and not credit_str:
        raw = parse_amount(debit_str)
        return -abs(raw)  # always negative
    if debit_str and credit_str:
        # Both filled – unusual; treat as net
        return parse_amount(credit_str) - parse_amount(debit_str)
    raise ValueError("Both debit and credit are empty")


def infer_sign_convention(amounts: list[int]) -> str:
    """Detect if a credit card export uses inverted signs (purchases positive).

    Returns 'normal' or 'inverted'.
    Requires at least 5 samples to make an inference.
    """
    if len(amounts) < 5:
        return "normal"  # too few rows to be sure
    pos = sum(1 for a in amounts if a > 0)
    neg = sum(1 for a in amounts if a < 0)
    if neg == 0 and pos > 0:
        # Every row is positive – inverted
        return "inverted"
    if pos > 0 and neg > 0 and pos > 3 * neg:
        # 75%+ positive – likely inverted
        return "inverted"
    return "normal"
