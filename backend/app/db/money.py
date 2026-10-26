"""Decimal <-> integer cents conversion at the DB boundary.

Rounding is ROUND_HALF_UP to the cent: ties move away from zero, so "1234.565" -> 123457
and "-1234.565" -> -123457. Floats are rejected outright so binary rounding never leaks in.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def to_decimal(value: Decimal | str | int) -> Decimal:
    if isinstance(value, float | bool):
        raise TypeError(f"money must not be {type(value).__name__}; use Decimal, str or int")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"not a valid amount: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"amount must be finite, got {value!r}")
    return amount


def quantize(value: Decimal | str | int) -> Decimal:
    amount = to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
    # Avoid "-0.00" leaking into output.
    return amount.copy_abs() if amount.is_zero() else amount


def to_cents(value: Decimal | str | int) -> int:
    return int(quantize(value).scaleb(2))


def from_cents(cents: int) -> Decimal:
    if not isinstance(cents, int) or isinstance(cents, bool):
        raise TypeError(f"cents must be int, got {type(cents).__name__}")
    return Decimal(cents).scaleb(-2)


def format_amount(value: Decimal | str | int) -> str:
    """Canonical string form with exactly two decimals, e.g. "-45.00"."""
    return f"{quantize(value):f}"
