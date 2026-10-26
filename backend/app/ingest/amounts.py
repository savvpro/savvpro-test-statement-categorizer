import re
from decimal import Decimal

_CURRENCY = r"(?:rs\.?|pkr|usd|\$)"
_LEADING_CURRENCY = re.compile(rf"^{_CURRENCY}\s*", re.IGNORECASE)
_TRAILING_CURRENCY = re.compile(rf"\s*{_CURRENCY}$", re.IGNORECASE)
# Plain digits, or digits grouped by commas in threes. Anything else is rejected.
_NUMBER = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+")


class AmountError(ValueError):
    """The text is not a clean money amount. The message is shown to the user."""


def parse_amount(text: str) -> Decimal:
    """Turn statement amount text into a Decimal. Negative means money out.

    Peels, from the outside in: whitespace, a currency marker (Rs, Rs., PKR, USD, $)
    at one end, one pair of parentheses (negative) or one leading "-" / "+".
    What is left must be digits with optional comma grouping in threes and an
    optional decimal part. Rejects, never guesses: empty text, letters, spaces or
    currency markers inside the number, malformed commas ("1,23.00"), European
    style ("1.234,56"), and more than one sign marker ("(-5)", "-(5)", "--5").
    """
    rest = text
    negative = False
    sign_markers = 0
    currency_markers = 0
    while True:
        before = rest
        rest = rest.strip().strip(" ").strip()
        rest, leading = _LEADING_CURRENCY.subn("", rest, count=1)
        rest, trailing = _TRAILING_CURRENCY.subn("", rest, count=1)
        currency_markers += leading + trailing
        if currency_markers > 1:
            raise AmountError(f"amount has more than one currency marker: {text.strip()!r}")
        if rest.startswith("(") and rest.endswith(")") and len(rest) >= 2:
            rest, negative, sign_markers = rest[1:-1], True, sign_markers + 1
        elif rest[:1] in ("-", "+"):
            negative = negative or rest[0] == "-"
            rest, sign_markers = rest[1:], sign_markers + 1
        if sign_markers > 1:
            raise AmountError(f"amount has more than one sign marker: {text.strip()!r}")
        if rest == before:
            break

    if not rest:
        raise AmountError("amount is empty")
    if not _NUMBER.fullmatch(rest):
        raise AmountError(f"amount is not a valid number: {text.strip()!r}")

    value = Decimal(rest.replace(",", ""))
    return -value if negative else value
