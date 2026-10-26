"""Date parsing with ambiguity detection.

Supports: MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, Month DD YYYY, DD Month YYYY
"""
from __future__ import annotations

import re
from datetime import date

_FORMATS_MDY = [
    "%m/%d/%Y", "%m/%d/%y",
    "%m-%d-%Y", "%m-%d-%y",
    "%m.%d.%Y", "%m.%d.%y",
]

_FORMATS_DMY = [
    "%d/%m/%Y", "%d/%m/%y",
    "%d-%m-%Y", "%d-%m-%y",
    "%d.%m.%Y", "%d.%m.%y",
]

_FORMATS_ISO = [
    "%Y-%m-%d", "%Y/%m/%d",
]

_FORMATS_NAMED = [
    "%b %d %Y", "%b %d, %Y",
    "%B %d %Y", "%B %d, %Y",
    "%d %b %Y", "%d %B %Y",
    "%b %d %y", "%d %b %y",
]

_ALL_FORMATS = _FORMATS_MDY + _FORMATS_DMY + _FORMATS_ISO + _FORMATS_NAMED


def _try_parse(value: str, fmt: str) -> date | None:
    try:
        from datetime import datetime
        return datetime.strptime(value.strip(), fmt).date()
    except (ValueError, TypeError):
        return None


def parse_date(value: str, *, prefer_mdy: bool = True) -> date:
    """Parse a date string, preferring US (MM/DD/YYYY) by default."""
    value = value.strip()

    # ISO always unambiguous
    for fmt in _FORMATS_ISO + _FORMATS_NAMED:
        d = _try_parse(value, fmt)
        if d:
            return d

    # Numeric: try both orders
    primary = _FORMATS_MDY if prefer_mdy else _FORMATS_DMY
    secondary = _FORMATS_DMY if prefer_mdy else _FORMATS_MDY

    for fmt in primary:
        d = _try_parse(value, fmt)
        if d:
            return d

    for fmt in secondary:
        d = _try_parse(value, fmt)
        if d:
            return d

    raise ValueError(f"Cannot parse date: {value!r}")


def infer_date_order(date_values: list[str]) -> tuple[bool, bool]:
    """
    Scan a column of date strings to decide if MDY or DMY is unambiguous.

    Returns (prefer_mdy: bool, is_ambiguous: bool).
    Ambiguous = could be either; caller should warn and default MDY.
    """
    mdy_only = 0  # count rows where day > 12 (so MDY is the only valid read)
    dmy_only = 0  # count rows where first part > 12 (so DMY must be used)
    both_valid = 0

    for v in date_values[:200]:  # scan up to 200 rows
        v = v.strip()
        # Match numeric dates like M/D/Y or D/M/Y
        m = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", v)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        a_is_valid_month = 1 <= a <= 12
        b_is_valid_month = 1 <= b <= 12

        if a_is_valid_month and b_is_valid_month:
            both_valid += 1
        elif a_is_valid_month and not b_is_valid_month:
            mdy_only += 1  # a=month, b=day>12 → MDY
        elif not a_is_valid_month and b_is_valid_month:
            dmy_only += 1  # a=day>12, b=month → DMY
        # else: both > 12 or both < 1 → malformed

    if dmy_only > 0 and mdy_only == 0:
        return False, False  # unambiguously DMY
    if mdy_only > 0 and dmy_only == 0:
        return True, False  # unambiguously MDY
    return True, True  # ambiguous → default MDY, warn
