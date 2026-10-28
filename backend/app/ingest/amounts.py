"""Money parsing: text -> Decimal -> integer cents."""

import re
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

MAX_ABS_DOLLARS = Decimal("1000000000")  # 1 billion; anything larger is junk
_CENT = Decimal("0.01")
_NUM_RE = re.compile(r"^(?:\d+(?:\.\d*)?|\.\d+)$")
_COMMA_DECIMAL_RE = re.compile(r"[,]\d{1,2}$")
_DOT_DECIMAL_RE = re.compile(r"[.]\d{1,2}$")
_SUFFIX_RE = re.compile(r"\s*\b(CR|DR)\b\.?$", re.IGNORECASE)
_CURRENCY_PREFIX_RE = re.compile(r"^(?:USD|US\$|\$)\s*", re.IGNORECASE)


class AmountError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_amount(raw: str, *, decimal_comma: bool = False) -> Decimal:
    """Parse a bank-statement amount. Debits are negative. Raises AmountError."""
    text = raw.strip().replace("−", "-").replace("–", "-").replace(" ", " ")
    if not text:
        raise AmountError("EMPTY_AMOUNT", "amount is empty")
    negative = False
    sign_override: int | None = None
    m = _SUFFIX_RE.search(text)
    if m:
        sign_override = 1 if m.group(1).upper() == "CR" else -1
        text = text[: m.start()].strip()
    text = _CURRENCY_PREFIX_RE.sub("", text).strip()
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    if text.endswith("-"):
        negative = True
        text = text[:-1].strip()
    if text.startswith("-"):
        negative = True
        text = text[1:].strip()
    elif text.startswith("+"):
        text = text[1:].strip()
    text = _CURRENCY_PREFIX_RE.sub("", text).strip()
    text = text.replace(" ", "")
    text = text.replace(".", "").replace(",", ".") if decimal_comma else text.replace(",", "")
    if not _NUM_RE.match(text):
        raise AmountError("BAD_AMOUNT", f"cannot parse amount {raw!r}")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:  # pragma: no cover - guarded by regex
        raise AmountError("BAD_AMOUNT", f"cannot parse amount {raw!r}") from exc
    if value > MAX_ABS_DOLLARS:
        raise AmountError("AMOUNT_TOO_LARGE", f"amount {raw!r} is out of range")
    if sign_override is not None:
        return abs(value) * sign_override
    return -value if negative else value


def has_extra_precision(value: Decimal) -> bool:
    return value != value.quantize(_CENT, rounding=ROUND_HALF_EVEN)


def to_cents(value: Decimal) -> int:
    return int((value.quantize(_CENT, rounding=ROUND_HALF_EVEN) * 100).to_integral_value())


def detect_decimal_comma(values: list[str]) -> bool:
    """Column-level: comma decimals only if some value ends ',dd' and none ends '.dd'."""
    comma = dot = 0
    for v in values:
        s = v.strip()
        s = _SUFFIX_RE.sub("", s).rstrip(")- ").strip()
        if _COMMA_DECIMAL_RE.search(s):
            comma += 1
        elif _DOT_DECIMAL_RE.search(s):
            dot += 1
    return comma > 0 and dot == 0


def format_cents(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole}.{frac:02d}"
