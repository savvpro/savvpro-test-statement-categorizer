"""Parsing of single cell values: money amounts and dates in the formats banks export."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_CURRENCY = re.compile(r"[$€£¥]|\b(?:USD|EUR|GBP|CAD)\b")
_NUMBER = re.compile(r"^\d+(?:\.\d+)?$")
_TIME_SUFFIX = re.compile(
    r"[ T]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:\s?[AP]M)?(?:Z|[+-]\d{2}:?\d{2})?$", re.I
)
CENT = Decimal("0.01")


def parse_amount(value: str | None) -> Decimal | None:
    """Parse ``$1,234.56``, ``(12.00)``, ``12.00-``, ``-$5``, ``1.234,56``, ``45.00 CR``...

    Returns the signed value as written, or ``None`` for an empty cell.
    Raises ``ValueError`` for text that is not an amount.
    """
    if value is None:
        return None
    s = value.strip().upper().replace(" ", "").replace("−", "-")
    if not s or s in {"-", "--"}:
        return None

    sign = 1
    if s.endswith("CR"):
        s = s[:-2].strip()
    elif s.endswith("DR"):
        s, sign = s[:-2].strip(), -1
    if s.startswith("(") and s.endswith(")"):
        s, sign = s[1:-1], -sign
    s = _CURRENCY.sub("", s).replace(" ", "")
    if s.endswith("-"):
        s, sign = s[:-1], -sign
    if s.startswith("-"):
        s, sign = s[1:], -sign
    elif s.startswith("+"):
        s = s[1:]
    s = _CURRENCY.sub("", s)

    if "," in s and "." in s:
        # Whichever separator comes last is the decimal point.
        s = (
            s.replace(".", "").replace(",", ".")
            if s.rfind(",") > s.rfind(".")
            else s.replace(",", "")
        )
    elif "," in s:
        s = s.replace(",", ".") if re.fullmatch(r"\d+,\d{2}", s) else s.replace(",", "")

    if not _NUMBER.match(s):
        raise ValueError(f"Not an amount: {value!r}")
    try:
        return (Decimal(s) * sign).quantize(CENT)
    except InvalidOperation as exc:  # pragma: no cover - guarded by the regex above
        raise ValueError(f"Not an amount: {value!r}") from exc


# Order matters: when a value fits several formats, the earlier (US) one wins.
DATE_FORMATS: tuple[str, ...] = (
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%b %d, %Y",
    "%b %d %Y",
    "%B %d, %Y",
    "%d %B %Y",
    "%Y%m%d",
)


def _clean_date(value: str) -> str:
    return _TIME_SUFFIX.sub("", value.strip()).strip()


def try_parse_date(value: str, fmt: str) -> date | None:
    try:
        return datetime.strptime(_clean_date(value), fmt).date()
    except ValueError:
        return None


def detect_date_format(values: Iterable[str]) -> tuple[str | None, list[str]]:
    """Pick the one format that reads (nearly) every date in a column.

    Choosing per file, not per value, avoids reading 03/04 as March in one row and
    April in the next. Returns the format and any warnings.
    """
    samples = [v for v in (_clean_date(v) for v in values if v) if v][:500]
    if not samples:
        return None, []
    scores: list[tuple[str, int]] = []
    for fmt in DATE_FORMATS:
        ok = sum(1 for v in samples if try_parse_date(v, fmt))
        if ok:
            scores.append((fmt, ok))
    if not scores:
        return None, []
    best = max(ok for _, ok in scores)
    if best < max(1, int(len(samples) * 0.8)):
        return None, []
    winners = [fmt for fmt, ok in scores if ok == best]
    chosen = winners[0]
    warnings = []
    if any(_day_month_swap(chosen, other) for other in winners[1:]):
        warnings.append(
            "Dates could be read as month/day or day/month; month/day (US) was assumed."
        )
    return chosen, warnings


def _day_month_swap(a: str, b: str) -> bool:
    return a.replace("%m", "X").replace("%d", "%m").replace("X", "%d") == b


def looks_like_date(value: str) -> bool:
    v = _clean_date(value)
    return bool(v) and any(try_parse_date(v, fmt) for fmt in DATE_FORMATS)


def looks_like_amount(value: str) -> bool:
    try:
        return parse_amount(value) is not None
    except ValueError:
        return False
