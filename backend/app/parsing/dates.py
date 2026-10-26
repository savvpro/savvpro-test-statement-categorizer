"""Date parsing with day/month order inferred from the whole column."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

# Month names are matched after accents and trailing dots are stripped, so "févr." and "fevr"
# are the same key. Abbreviations that mean different months in two languages do not exist
# among the ones listed here.
_MONTH_NAMES: tuple[tuple[str, ...], ...] = (
    ("jan", "january", "janv", "janvier", "januari", "ene", "enero", "januar"),
    ("feb", "february", "fev", "fevr", "fevrier", "februari", "febrero", "februar"),
    ("mar", "march", "mars", "mrt", "maart", "marzo", "marz", "maerz"),
    ("apr", "april", "avr", "avril", "abr", "abril"),
    ("may", "mai", "mei", "mayo"),
    ("jun", "june", "juin", "juni", "junio"),
    ("jul", "july", "juil", "juillet", "juli", "julio"),
    ("aug", "august", "aout", "augustus", "ago", "agosto"),
    ("sep", "sept", "september", "septembre", "septiembre", "setiembre"),
    ("oct", "october", "octobre", "okt", "oktober", "octubre"),
    ("nov", "november", "novembre", "noviembre"),
    ("dec", "december", "decembre", "dez", "dezember", "dic", "diciembre"),
)
_MONTHS = {name: i for i, names in enumerate(_MONTH_NAMES, start=1) for name in names}
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))

_ORDINAL = r"(?:st|nd|rd|th|er|e)?"
_ISO = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[T\s].*)?$")
_NUMERIC = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})(?:[T\s].*)?$")
_NUMERIC_NO_YEAR = re.compile(r"^(\d{1,2})[-/.](\d{1,2})\.?$")
_DAY_MONTH_NAME = re.compile(
    rf"^(\d{{1,2}}){_ORDINAL}[-\s/.]*([A-Za-z]{{3,12}})\.?,?[-\s/.]*(\d{{2}}|\d{{4}})?$"
)
_MONTH_NAME_DAY = re.compile(
    rf"^([A-Za-z]{{3,12}})\.?[-\s/.]+(\d{{1,2}}){_ORDINAL},?[-\s/.]*(\d{{2}}|\d{{4}})?$"
)

# A date at the very start of a longer piece of text (a description with the date in front).
_DATE_PREFIX = re.compile(
    rf"""^\s*(?P<date>
        \d{{4}}-\d{{2}}-\d{{2}}
      | \d{{1,2}}[/.-]\d{{1,2}}[/.-](?:\d{{4}}|\d{{2}})(?!\d)
      | \d{{1,2}}{_ORDINAL}[-\s/.]*(?:{_MONTH_ALT})\.?
        (?:,?[-\s/.]+(?:\d{{4}}|\d{{2}})(?!\d))?(?![A-Za-z])
      | (?:{_MONTH_ALT})\.?\s+\d{{1,2}}{_ORDINAL}(?:,?\s+\d{{4}}(?!\d))?(?![\d])
      | \d{{1,2}}/\d{{1,2}}(?![\d/])
    )(?:\s+|$)""",
    re.I | re.X,
)

DMY = "dmy"
MDY = "mdy"


@dataclass(frozen=True)
class DateOrder:
    order: str  # "dmy" or "mdy"
    ambiguous: bool  # True when no value in the column could settle it


def _plain(text: str) -> str:
    if text.isascii():
        return text
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def month_number(name: str) -> int | None:
    """Month for an English, French, Dutch, Spanish or German name or abbreviation."""
    return _MONTHS.get(_plain(name).lower().strip(". "))


def _full_year(raw: str | None, default_year: int | None) -> int | None:
    if raw is None:
        return default_year
    year = int(raw)
    if len(raw) == 2:
        year += 2000 if year < 70 else 1900
    return year


def _make(year: int | None, month: int, day: int) -> date | None:
    if year is None or not (1990 <= year <= 2100):
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def infer_date_order(samples: Iterable[str]) -> DateOrder:
    """Look at every numeric a/b[/year] value to decide whether the first part is day or month."""
    first_gt_12 = second_gt_12 = False
    for raw in samples:
        text = raw.strip()
        m = _NUMERIC.match(text) or _NUMERIC_NO_YEAR.match(text)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        first_gt_12 |= a > 12
        second_gt_12 |= b > 12
    if first_gt_12 and not second_gt_12:
        return DateOrder(DMY, False)
    if second_gt_12 and not first_gt_12:
        return DateOrder(MDY, False)
    return DateOrder(MDY, True)


def has_year(text: str) -> bool:
    """True when a date string carries its own year (so it needs no year inference)."""
    s = _plain(text.strip())
    if _ISO.match(s):
        return True
    if _NUMERIC.match(s):
        return True
    m = _DAY_MONTH_NAME.match(s)
    if m:
        return m.group(3) is not None
    m = _MONTH_NAME_DAY.match(s)
    return bool(m and m.group(3) is not None)


def parse_date(text: str | None, order: str = MDY, default_year: int | None = None) -> date | None:
    if text is None:
        return None
    s = _plain(str(text).strip())
    if not s:
        return None

    m = _ISO.match(s)
    if m:
        return _make(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    m = _NUMERIC.match(s)
    if m:
        a, b, year = int(m.group(1)), int(m.group(2)), _full_year(m.group(3), None)
        day, month = (a, b) if order == DMY else (b, a)
        return _make(year, month, day)

    m = _DAY_MONTH_NAME.match(s)
    if m:
        written_month = month_number(m.group(2))
        if written_month:
            return _make(_full_year(m.group(3), default_year), written_month, int(m.group(1)))

    m = _MONTH_NAME_DAY.match(s)
    if m:
        named_month = month_number(m.group(1))
        if named_month:
            return _make(_full_year(m.group(3), default_year), named_month, int(m.group(2)))

    m = _NUMERIC_NO_YEAR.match(s)
    if m and default_year is not None:
        a, b = int(m.group(1)), int(m.group(2))
        day, month = (a, b) if order == DMY else (b, a)
        return _make(default_year, month, day)

    return None


def split_date_prefix(text: str) -> tuple[str, str] | None:
    """Split "02 janv. 25 SKIP PLATS" into ("02 janv. 25", "SKIP PLATS").

    Returns None when the text does not start with something that parses as a date.
    """
    plain = _plain(text)
    m = _DATE_PREFIX.match(plain)
    if not m:
        return None
    head = m.group("date").strip()
    if parse_date(head, MDY, 2000) is None and parse_date(head, DMY, 2000) is None:
        return None
    rest = text[m.end() :] if len(plain) == len(text) else plain[m.end() :]
    return head, rest.strip()


_YEAR_IN_DATE = re.compile(
    rf"""(?:
        \b\d{{1,2}}[/.-]\d{{1,2}}[/.-](?P<y1>(?:19|20)\d{{2}})\b
      | \b(?P<y2>(?:19|20)\d{{2}})-\d{{2}}-\d{{2}}\b
      | \b\d{{1,2}}{_ORDINAL}[-\s/.]*(?:{_MONTH_ALT})\.?,?\s+(?P<y3>(?:19|20)\d{{2}})\b
      | \b(?:{_MONTH_ALT})\.?\s+\d{{1,2}}{_ORDINAL},?\s+(?P<y4>(?:19|20)\d{{2}})\b
    )""",
    re.I | re.X,
)
_ANY_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def guess_year(text: str) -> int | None:
    """Best year for dates that print none, from the dates written out in full in the text.

    Years that sit inside complete dates win over any other four-digit number, and the most
    common one wins (a tie goes to the later year, since statements talk about the past).
    """
    plain = _plain(text)
    counts: Counter[int] = Counter()
    for m in _YEAR_IN_DATE.finditer(plain):
        year = next(g for g in m.groups() if g)
        counts[int(year)] += 1
    if not counts:
        counts.update(int(y) for y in _ANY_YEAR.findall(plain))
    if not counts:
        return None
    return max(counts, key=lambda y: (counts[y], y))


def fix_year_rollover(
    dates: Sequence[date | None], yearless: Sequence[bool], reference_year: int | None
) -> list[date | None]:
    """Move yearless dates that belong before the reference year back by one year.

    A statement that spans New Year prints "Dec 28" and "Jan 03" with no year. The months
    seen on yearless lines form an arc on the calendar; when that arc crosses December into
    January, the months before the wrap belong to the previous year.
    """
    result = list(dates)
    if reference_year is None:
        return result
    months = sorted({d.month for d, flag in zip(dates, yearless, strict=True) if flag and d})
    if len(months) < 2:
        return result
    gaps = [
        ((months[(i + 1) % len(months)] - m - 1) % 12, m) for i, m in enumerate(months)
    ]  # months left empty after each present month, going round the calendar
    largest, before_gap = max(gaps)
    if largest < 6:
        return result  # spread over most of the year: no wrap can be told from the months
    start = months[(months.index(before_gap) + 1) % len(months)]
    if start <= before_gap:
        return result  # the arc does not cross the year boundary
    for i, (d, flag) in enumerate(zip(dates, yearless, strict=True)):
        if flag and d is not None and d.month >= start:
            result[i] = _make(d.year - 1, d.month, d.day) or d
    return result
