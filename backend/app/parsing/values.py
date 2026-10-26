"""Reading amounts, dates and descriptions out of statement text.

Everything here refuses to guess. If a value can be read more than one way,
it raises an error that explains what to fix.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


class ValueProblem(ValueError):
    """A single value (one cell) could not be read safely."""


class NeedsUserChoice(ValueError):
    """The whole file is ambiguous and the user has to pick an option."""


class UnsupportedFile(ValueError):
    """The file can't be read at all (wrong format, damaged, unknown layout)."""


# --- amounts -----------------------------------------------------------------

_CURRENCY_MARKS = re.compile(r"US\$|\$|\b(?:PKR|USD|RS\.?)(?=\s|\d|$)")
_GROUPED = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?$")
_PLAIN = re.compile(r"^\d+(?:\.\d{1,2})?$")


def parse_amount(raw) -> Decimal:
    """Turn '1,250.00', '(1,250.00)', '1,250.00 DR', 'Rs. 500' or '-12.50' into a signed Decimal."""
    if raw is None:
        raise ValueProblem("amount is missing")
    original = str(raw).strip()
    text = original.upper().replace("\u2212", "-").replace("\u00a0", " ")  # unicode minus, no-break space
    if not text:
        raise ValueProblem("amount is missing")

    negative = False
    if text.endswith("DR"):
        negative, text = True, text[:-2].strip()
    elif text.endswith("CR"):
        text = text[:-2].strip()

    text = _CURRENCY_MARKS.sub("", text).strip()

    if text.startswith("(") and text.endswith(")"):
        if negative:
            raise ValueProblem(f"amount '{original}' has two minus markers")
        negative, text = True, text[1:-1].strip()
    if text.startswith("-") or text.endswith("-"):
        if negative:
            raise ValueProblem(f"amount '{original}' has two minus markers")
        negative, text = True, text.strip("-").strip()
    if text.startswith("+"):
        text = text[1:].strip()

    if not (_GROUPED.match(text) or _PLAIN.match(text)):
        raise ValueProblem(f"amount '{original}' is not in a format the app can read safely")
    try:
        value = Decimal(text.replace(",", ""))
    except InvalidOperation as exc:  # pragma: no cover - regex already filters this
        raise ValueProblem(f"amount '{original}' could not be read") from exc
    return -value if negative else value


def to_minor(amount: Decimal) -> int:
    """PKR and USD both use two decimal places, so amounts are stored as paisa / cents."""
    return int((amount * 100).to_integral_value())


def from_minor(minor: int) -> Decimal:
    return (Decimal(minor) / 100).quantize(Decimal("0.01"))


def currency_from_text(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip().upper()
    if text in {"PKR", "RS", "RS.", "RUPEES", "PAK RUPEE"}:
        return "PKR"
    if text in {"USD", "$", "US$", "US DOLLAR", "DOLLARS"}:
        return "USD"
    raise ValueProblem(f"currency '{raw.strip()}' is not supported (only PKR and USD)")


def currency_hint(text: str) -> str | None:
    """Look for a currency marker inside free text such as a header or an amount."""
    upper = text.upper()
    found = set()
    if re.search(r"\bPKR\b|\bRS\.?\s?\d", upper):
        found.add("PKR")
    if re.search(r"\bUSD\b|\$", upper):
        found.add("USD")
    return found.pop() if len(found) == 1 else None


# --- dates -------------------------------------------------------------------

_NUMERIC_DATE = re.compile(r"^(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{2,4})$")
_TEXT_FORMATS = (
    "%d %b %Y", "%d-%b-%Y", "%d/%b/%Y", "%d %b %y", "%d-%b-%y",
    "%d %B %Y", "%d-%B-%Y", "%b %d, %Y", "%B %d, %Y", "%b %d %Y",
)

DAY_FIRST = "day_first"
MONTH_FIRST = "month_first"
AUTO = "auto"


def _numeric_parts(text: str):
    match = _NUMERIC_DATE.match(text.strip())
    if not match:
        return None
    a, b, c = match.groups()
    if len(a) == 4:  # 2026-01-31 style, never ambiguous
        return None
    return int(a), int(b)


def resolve_date_order(values: list[str], requested: str = AUTO) -> str:
    """Decide whether 03/04/2026 means 3 April or 4 March, for the whole file.

    One file uses one format, so the decision is made once from all the dates.
    """
    day_first_proof = month_first_proof = None
    has_ambiguous = False
    for value in values:
        parts = _numeric_parts(value)
        if not parts:
            continue
        a, b = parts
        if a > 12:
            day_first_proof = value
        elif b > 12:
            month_first_proof = value
        else:
            has_ambiguous = True

    if day_first_proof and month_first_proof:
        raise NeedsUserChoice(
            f"The dates in this file disagree ('{day_first_proof}' is day-first, "
            f"'{month_first_proof}' is month-first). Check the file."
        )
    if requested == DAY_FIRST and month_first_proof:
        raise NeedsUserChoice(f"You chose day-first, but '{month_first_proof}' can only be month-first.")
    if requested == MONTH_FIRST and day_first_proof:
        raise NeedsUserChoice(f"You chose month-first, but '{day_first_proof}' can only be day-first.")
    if requested in (DAY_FIRST, MONTH_FIRST):
        return requested
    if day_first_proof:
        return DAY_FIRST
    if month_first_proof:
        return MONTH_FIRST
    if has_ambiguous:
        raise NeedsUserChoice(
            "Every date in this file could be read two ways (for example 03/04/2026). "
            "Choose day-first or month-first and upload again."
        )
    return DAY_FIRST  # no numeric dates at all, so the order does not matter


def parse_date(raw: str, order: str) -> date:
    text = (raw or "").strip()
    if not text:
        raise ValueProblem("date is missing")
    match = _NUMERIC_DATE.match(text)
    if match:
        a, b, c = (int(x) for x in match.groups())
        if len(match.group(1)) == 4:
            year, month, day = a, b, c
        else:
            year = c + 2000 if c < 100 else c
            day, month = (a, b) if order == DAY_FIRST else (b, a)
        try:
            return date(year, month, day)
        except ValueError as exc:
            raise ValueProblem(f"date '{text}' is not a real date") from exc
    cleaned = re.sub(r"\s+", " ", text.title())
    for fmt in _TEXT_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueProblem(f"date '{text}' could not be read")


# --- descriptions ------------------------------------------------------------

def normalize_description(text: str) -> str:
    """Upper-case, drop punctuation the rules don't care about, squeeze spaces."""
    upper = (text or "").upper()
    upper = re.sub(r"[^A-Z0-9&*.@ ]+", " ", upper)
    upper = re.sub(r"(?<![A-Z0-9])\.|\.(?![A-Z0-9])", " ", upper)
    return re.sub(r"\s+", " ", upper).strip()


_NOISE_WORDS = {"POS", "TXN", "REF", "PURCHASE", "ONLINE", "DEBIT", "CARD", "PAYMENT", "TRX", "ID"}


def suggest_rule_pattern(description: str) -> str:
    """Best guess at the merchant part of a description, for the 'make a rule' form.

    'POS 4471 JOES CAFE 9921' -> 'JOES CAFE'. The user can edit it before saving.
    """
    words = [
        w for w in normalize_description(description).split()
        if not any(ch.isdigit() for ch in w) and w not in _NOISE_WORDS and w != "*"
    ]
    return " ".join(words[:3])
