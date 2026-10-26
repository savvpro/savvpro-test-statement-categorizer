"""Date strings -> date. The day/month order is decided once per column, never per row."""

import datetime as dt
import re
from collections.abc import Iterable
from enum import StrEnum

MIN_YEAR = 2000

_ISO_RE = re.compile(
    r"^(?P<y>\d{4})[-/.](?P<m>\d{1,2})[-/.](?P<d>\d{1,2})"
    r"(?:[T ]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$"  # optional time part
)
_NUMERIC_RE = re.compile(r"^(?P<a>\d{1,2})[-/.](?P<b>\d{1,2})[-/.](?P<y>\d{4}|\d{2})$")
_DAY_MONTH_RE = re.compile(
    r"^(?P<d>\d{1,2})[\s-]+(?P<mon>[A-Za-z]{3,9})\.?[\s,-]+(?P<y>\d{4}|\d{2})$"
)
_MONTH_DAY_RE = re.compile(
    r"^(?P<mon>[A-Za-z]{3,9})\.?\s+(?P<d>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<y>\d{4})$",
    re.IGNORECASE,
)

_MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]  # fmt: skip
_MONTHS = {name: i for i, full in enumerate(_MONTH_NAMES, 1) for name in (full, full[:3])}
_MONTHS["sept"] = 9


class DateOrder(StrEnum):
    month_first = "month_first"  # 01/05/2026 is January 5 (US default)
    day_first = "day_first"  # 01/05/2026 is 1 May
    unambiguous = "unambiguous"  # only ISO or month-name dates in the column


def detect_date_order(values: Iterable[str]) -> DateOrder:
    """Day-first if any numeric date has a first part above 12, otherwise month-first."""
    saw_numeric = False
    for value in values:
        if match := _NUMERIC_RE.match(value.strip()):
            saw_numeric = True
            if int(match["a"]) > 12:
                return DateOrder.day_first
    return DateOrder.month_first if saw_numeric else DateOrder.unambiguous


def parse_date(text: str, order: DateOrder = DateOrder.month_first) -> dt.date:
    value = text.strip()
    if match := _ISO_RE.match(value):
        year, month, day = int(match["y"]), int(match["m"]), int(match["d"])
    elif match := _NUMERIC_RE.match(value):
        a, b = int(match["a"]), int(match["b"])
        month, day = (b, a) if order is DateOrder.day_first else (a, b)
        year = int(match["y"])
    elif match := _DAY_MONTH_RE.match(value) or _MONTH_DAY_RE.match(value):
        month = _month_number(match["mon"], value)
        day, year = int(match["d"]), int(match["y"])
    else:
        raise ValueError(f"unrecognized date {value!r}")

    if year < 100:
        year += 2000
    max_year = dt.date.today().year + 1
    if not MIN_YEAR <= year <= max_year:
        raise ValueError(f"date {value!r} is outside {MIN_YEAR}..{max_year}")
    try:
        return dt.date(year, month, day)
    except ValueError:
        raise ValueError(f"invalid date {value!r}") from None


def _month_number(name: str, value: str) -> int:
    try:
        return _MONTHS[name.lower()]
    except KeyError:
        raise ValueError(f"unknown month in date {value!r}") from None
