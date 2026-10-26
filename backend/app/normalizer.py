import re

_MASKED = re.compile(r"\S*\*{2,}\S*")  # 0042****7781, 0300****412
_USD = re.compile(r"\bUSD\b\s*[\d,]*\.?\d*")
_ORDER_ID = re.compile(r"\d+|(?=[A-Z0-9]*\d)[A-Z0-9]{5,}")  # 4471920, 2K4LP8


def has_usd(description: str) -> bool:
    return bool(_USD.search(description.upper()))


def normalize(description: str) -> str:
    """Uppercase, drop masked digits, USD amounts, '*' and trailing order or store numbers."""
    text = _USD.sub(" ", _MASKED.sub(" ", description.upper())).replace("*", " ")
    tokens = text.split()
    while tokens and _ORDER_ID.fullmatch(tokens[-1]):
        tokens.pop()
    return " ".join(tokens)
