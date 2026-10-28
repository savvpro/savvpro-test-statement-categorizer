"""Column-level date-format inference and OFX date parsing."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

CANDIDATE_FORMATS: tuple[str, ...] = (
    "%m/%d/%Y",
    "%m/%d/%y",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%b-%Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%m-%d-%Y",
    "%Y%m%d",
)
_AMBIGUOUS_PAIRS = (("%m/%d/%Y", "%d/%m/%Y"), ("%m/%d/%y", "%d/%m/%y"))
_TIME_TAIL_RE = re.compile(r"[T\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\s*(?:[APap][Mm])?Z?$")
_OFX_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(?:\d{2,}(?:\.\d+)?)?(?:\[.*\])?$")
MIN_YEAR = 2000
FUTURE_GRACE_DAYS = 7


class DateError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class DateInference:
    fmt: str | None
    ambiguous: bool


def _clean(raw: str) -> str:
    text = raw.strip()
    if len(text) > 10:
        text = _TIME_TAIL_RE.sub("", text)
    return text


def _try(raw: str, fmt: str) -> date | None:
    try:
        return datetime.strptime(_clean(raw), fmt).date()
    except ValueError:
        return None


def infer_format(values: Sequence[str]) -> DateInference:
    """Pick the format parsing every value; MDY wins when MDY and DMY both fit."""
    vals = [v for v in values if v.strip()]
    if not vals:
        return DateInference(None, False)
    scores = {fmt: sum(1 for v in vals if _try(v, fmt) is not None) for fmt in CANDIDATE_FORMATS}
    full = [f for f in CANDIDATE_FORMATS if scores[f] == len(vals)]
    if full:
        chosen = full[0]
        ambiguous = any(a in full and b in full for a, b in _AMBIGUOUS_PAIRS) and chosen in {
            a for a, _ in _AMBIGUOUS_PAIRS
        }
        return DateInference(chosen, ambiguous)
    best = max(CANDIDATE_FORMATS, key=lambda f: (scores[f], -CANDIDATE_FORMATS.index(f)))
    if scores[best] == 0:
        return DateInference(None, False)
    return DateInference(best, False)


def parse_date(raw: str, fmt: str) -> date:
    """Parse with the chosen format. Raises DateError for junk or pre-2000 years."""
    if fmt == "ofx":
        return parse_ofx_date(raw)
    parsed = _try(raw, fmt)
    if parsed is None:
        raise DateError("BAD_DATE", f"cannot parse date {raw!r}")
    if parsed.year < MIN_YEAR:
        raise DateError("DATE_TOO_OLD", f"date {raw!r} is before {MIN_YEAR}")
    return parsed


def parse_ofx_date(raw: str) -> date:
    """YYYYMMDD[HHMMSS[.XXX]][[+-]TZ[:name]] -> date part."""
    text = raw.strip()
    m = _OFX_RE.match(text)
    if not m:
        raise DateError("BAD_DATE", f"cannot parse OFX date {raw!r}")
    try:
        parsed = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError as exc:
        raise DateError("BAD_DATE", f"invalid OFX date {raw!r}") from exc
    if parsed.year < MIN_YEAR:
        raise DateError("DATE_TOO_OLD", f"date {raw!r} is before {MIN_YEAR}")
    return parsed


def is_future(d: date, today: date | None = None) -> bool:
    return d > (today or date.today()) + timedelta(days=FUTURE_GRACE_DAYS)
