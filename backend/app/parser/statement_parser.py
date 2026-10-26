"""CSV statement parser.

Real statements vary wildly, so the parser is deliberately lenient:

- Column names vary (Description / Name / Payee, Amount / Transaction Amount,
  or separate Debit + Credit columns, or an Amount + Type pair). We auto-map
  from a list of known aliases.
- Amounts may be signed (negative = spend), in accounting style with
  parentheses "(54.99)", or unsigned with a DEBIT/CREDIT type column.
- Dates come in many formats; we try the common ones (US month-first first).
- Statement furniture rows ("Total", "Ending Balance") are skipped, not
  categorized.
- Bad rows never crash the upload: they are flagged row-by-row and land in
  Needs Review, because "a wrong guess is worse than asking".
"""

import csv
import io
from datetime import datetime

from ..models import ParsedTransaction, ParseMeta

# Header aliases, first match wins. Headers are compared lowercased with
# punctuation collapsed to spaces.
FIELD_ALIASES: dict[str, list[str]] = {
    "date": ["date", "transaction date", "post date", "posted date", "trans date"],
    "description": ["description", "name", "details", "payee", "memo", "transaction",
                    "narrative", "merchant"],
    "amount": ["amount", "transaction amount", "value"],
    "debit": ["debit", "withdrawal", "money out"],
    "credit": ["credit", "deposit", "money in"],
    "type": ["type", "dr cr", "debit credit", "direction"],
}

DATE_FORMATS = [
    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d",
    "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
    "%d-%m-%Y", "%d.%m.%Y",
]

SKIP_LABELS = {
    "total", "subtotal", "ending balance", "beginning balance",
    "previous balance", "balance", "payments and adjustments",
}


class ParseError(Exception):
    """Raised when the file cannot be parsed at all (bad header, empty file)."""


def _clean_header(h: str) -> str:
    h = h.strip().lower()
    out = []
    for ch in h:
        out.append(ch if ch.isalnum() else " ")
    return " ".join("".join(out).split())


def _map_columns(fieldnames: list[str]) -> dict[str, str]:
    """Map logical fields -> actual CSV column names using known aliases."""
    norm_to_raw = {_clean_header(fn): fn for fn in fieldnames if fn}
    mapping: dict[str, str] = {}
    for logical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in norm_to_raw:
                mapping[logical] = norm_to_raw[alias]
                break
    has_amount = "amount" in mapping
    has_dc = "debit" in mapping and "credit" in mapping
    if "date" not in mapping or "description" not in mapping or not (has_amount or has_dc):
        raise ParseError(
            "Could not find the required columns. Need a date column, a description "
            "column, and either 'Amount' or 'Debit'+'Credit' columns. "
            f"Headers found: {fieldnames}"
        )
    return mapping


def _parse_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_amount(raw: str) -> float | None:
    s = (raw or "").replace("$", "").replace(",", "").replace(" ", "").strip()
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def _row_amount(row: dict, mapping: dict) -> tuple[float | None, str | None]:
    """Resolve the signed amount for a row. Negative = money out (spending)."""
    if "debit" in mapping and "credit" in mapping:
        debit = _parse_amount(row.get(mapping["debit"], ""))
        credit = _parse_amount(row.get(mapping["credit"], ""))
        if debit is None and credit is None:
            return None, "missing amount"
        return -(debit or 0.0) + (credit or 0.0), None

    amount = _parse_amount(row.get(mapping.get("amount", ""), ""))
    if amount is None:
        return None, "missing amount"

    type_col = mapping.get("type")
    if type_col:
        t = (row.get(type_col) or "").strip().upper()
        if t in {"DEBIT", "DR", "OUT"}:
            amount = -abs(amount)
        elif t in {"CREDIT", "CR", "IN"}:
            amount = abs(amount)
    return amount, None


def parse_statement(text: str) -> tuple[list[ParsedTransaction], ParseMeta, list[str]]:
    """Parse statement CSV text into transactions + metadata + warnings."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ParseError("The file is empty or has no header row.")

    mapping = _map_columns(reader.fieldnames)
    meta = ParseMeta()
    warnings: list[str] = []
    txns: list[ParsedTransaction] = []

    for row in reader:
        meta.rows_read += 1
        desc_raw = (row.get(mapping["description"]) or "").strip()
        date_raw = (row.get(mapping["date"]) or "").strip()
        amount_raw = (row.get(mapping.get("amount", "")) or "").strip()

        # Skip fully empty lines
        if not desc_raw and not date_raw and not amount_raw:
            meta.rows_read -= 1
            continue

        # Skip statement furniture ("Total", "Ending balance", ...)
        label = _clean_header(desc_raw)
        if label in SKIP_LABELS:
            meta.rows_skipped += 1
            meta.skipped_labels.append(desc_raw)
            continue

        issues: list[str] = []
        amount, amount_issue = _row_amount(row, mapping)
        if amount_issue:
            issues.append(amount_issue)
            amount = 0.0

        iso_date = _parse_date(date_raw)
        if date_raw and iso_date is None:
            issues.append("unreadable date")

        txns.append(ParsedTransaction(
            date_raw=date_raw,
            date=iso_date,
            description=desc_raw or "(no description)",
            amount=round(amount or 0.0, 2),
            issues=issues,
        ))
        meta.rows_kept += 1

    if meta.rows_kept == 0:
        raise ParseError("No usable transaction rows were found in the file.")

    if meta.rows_skipped:
        warnings.append(
            f"Skipped {meta.rows_skipped} summary row(s): "
            f"{', '.join(dict.fromkeys(meta.skipped_labels))}")
    bad_dates = sum(1 for t in txns if "unreadable date" in t.issues)
    if bad_dates:
        warnings.append(f"{bad_dates} row(s) had unreadable dates and went to Needs Review")
    bad_amounts = sum(1 for t in txns if "missing amount" in t.issues)
    if bad_amounts:
        warnings.append(f"{bad_amounts} row(s) had missing amounts and went to Needs Review")

    return txns, meta, warnings
