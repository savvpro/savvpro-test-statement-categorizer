from decimal import Decimal

# SQLite has no exact decimal type, so money is stored as an integer count of minor units
# (paisa / cents) and converted to and from Decimal here, at the boundary. Both currencies
# in the sample data have two decimal places.
MINOR_DIGITS = 2


class MoneyError(ValueError):
    pass


def to_minor(amount: Decimal) -> int:
    """Exact conversion. Raises MoneyError if the amount has more decimals than we can store."""
    sign, digits, exponent = amount.as_tuple()
    if not isinstance(exponent, int):
        raise MoneyError("amount is not a finite number")
    number = int("".join(map(str, digits)) or "0")
    shift = exponent + MINOR_DIGITS
    if shift >= 0:
        minor = number * 10**shift
    else:
        divisor = 10**-shift
        if number % divisor:
            raise MoneyError(f"amount has more than {MINOR_DIGITS} decimal places")
        minor = number // divisor
    return -minor if sign else minor


def from_minor(minor: int) -> Decimal:
    return Decimal(minor).scaleb(-MINOR_DIGITS)
