"""Tolerant money parsing for the many ways statements print an amount."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CURRENCY_CODES = (
    "USD",
    "EUR",
    "GBP",
    "CAD",
    "AUD",
    "NZD",
    "CHF",
    "JPY",
    "INR",
    "PKR",
    "AED",
    "SGD",
    "HKD",
    "SEK",
    "NOK",
    "DKK",
    "ZAR",
    "CNY",
    "MXN",
    "BRL",
    "PLN",
    "CZK",
    "HUF",
    "TRY",
    "THB",
    "MYR",
    "IDR",
    "PHP",
    "KRW",
    "SAR",
    "QAR",
    "KWD",
    "BDT",
    "LKR",
    "NGN",
    "KES",
)
_CURRENCY_CODE = re.compile(r"\b(?:" + "|".join(CURRENCY_CODES) + r")\b", re.I)
_SYMBOLS = re.compile(r"[$€£¥₹₨\ufffd]|Rs\.?", re.I)
_SUFFIX = re.compile(r"(?<=[\d)])\s*(CR|DR)\.?$", re.I)
_PREFIX = re.compile(r"^(CR|DR)\.?\s*(?=[\d(\-+$€£])", re.I)
_VALID = re.compile(r"^(?:\d+(?:\.\d+)?|\.\d+)$")
_CENT = Decimal("0.01")

# Symbols that name one currency in practice. "$" is read as US dollars unless a code says
# otherwise, since the symbol alone cannot tell the dollar currencies apart.
_SYMBOL_CURRENCY = {
    "£": "GBP",
    "€": "EUR",
    "$": "USD",
    "¥": "JPY",
    "₹": "INR",
}
_SYMBOL_FINDER = re.compile(r"[£€$¥₹]")
_RS = re.compile(r"\bRs\.?(?=\s*\d)", re.I)


@dataclass(frozen=True)
class ParsedAmount:
    value: Decimal  # signed as printed (parentheses and trailing minus become negative)
    suffix: str | None = None  # "CR" or "DR" when the file printed one
    currency: str | None = None  # ISO code when the text carried a symbol or a code


def detect_currency(text: str | None) -> str | None:
    """ISO code for a currency symbol or code found anywhere in `text`, else None."""
    if not text:
        return None
    code = _CURRENCY_CODE.search(text)
    if code:
        return code.group(0).upper()
    symbol = _SYMBOL_FINDER.search(text)
    if symbol:
        return _SYMBOL_CURRENCY[symbol.group(0)]
    if _RS.search(text):
        return "INR"
    return None


def parse_amount(text: str | None) -> ParsedAmount | None:
    """Parse an amount string. Returns None when it is not a recognisable number."""
    if text is None:
        return None
    raw = str(text)
    s = raw.strip().replace("\u00a0", " ").replace("\u2212", "-").replace("\u202f", " ")
    if not s:
        return None
    currency = detect_currency(s)

    suffix: str | None = None
    match = _SUFFIX.search(s)
    if match:
        suffix = match.group(1).upper()
        s = s[: match.start()].strip()
    else:
        match = _PREFIX.match(s)
        if match:
            suffix = match.group(1).upper()
            s = s[match.end() :].strip()

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = _CURRENCY_CODE.sub("", s)
    s = _SYMBOLS.sub("", s)
    s = s.replace(" ", "").replace("'", "").replace("\u2019", "").strip()
    if s.endswith("-"):
        negative = True
        s = s[:-1]
    if s.startswith("+"):
        s = s[1:]
    if s.startswith("-"):
        negative = True
        s = s[1:]

    s = _normalise_separators(s)
    if not _VALID.match(s):
        return None
    try:
        value = Decimal(s).quantize(_CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None
    return ParsedAmount(-value if negative else value, suffix, currency)


def _normalise_separators(s: str) -> str:
    has_dot = "." in s
    has_comma = "," in s
    if has_dot and has_comma:
        decimal_sep = "." if s.rfind(".") > s.rfind(",") else ","
        thousands_sep = "," if decimal_sep == "." else "."
        s = s.replace(thousands_sep, "")
        return s.replace(decimal_sep, ".")
    if has_comma:
        parts = s.split(",")
        # A single comma followed by one or two digits is a decimal comma ("12,50").
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            return f"{parts[0]}.{parts[1]}"
        return s.replace(",", "")
    if has_dot and s.count(".") > 1:
        return s.replace(".", "")  # "1.234.567"
    return s
