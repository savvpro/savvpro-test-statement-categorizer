import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

REQUIRED = ("date", "description", "amount")
# Day-first before month-first: the client is Australian, so 03/10/2026 = 3 Oct.
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%m/%d/%Y")
MAX_AMOUNT = Decimal("1000000000000")


class StatementError(ValueError):
    """File-level problem: empty file, bad encoding, missing columns."""


def parse_amount(raw: str) -> Decimal:
    """'-45.00', '(45.00)', '$1,200.50', '45.00-' -> Decimal (negative = money out)."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty amount")
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[()$£€\s,]", "", text)
    if text.endswith("-"):
        negative, text = True, text[:-1]
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"invalid amount: {raw!r}") from None
    if not value.is_finite() or abs(value) > MAX_AMOUNT:
        raise ValueError(f"invalid amount: {raw!r}")
    return -abs(value) if negative else value


def parse_date(raw: str) -> str:
    text = (raw or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"invalid date: {raw!r}")


def parse_statement(content: bytes):
    """Return (rows, errors). Bad rows go to errors; the rest still work."""
    if not content.strip():
        raise StatementError("File is empty")
    try:
        text = content.decode("utf-8-sig")  # utf-8-sig strips Excel's BOM
    except UnicodeDecodeError:
        raise StatementError("File is not a text CSV (invalid encoding)") from None

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise StatementError("No header row found")
    reader.fieldnames = [(h or "").strip().lower() for h in reader.fieldnames]
    missing = [c for c in REQUIRED if c not in reader.fieldnames]
    if missing:
        raise StatementError("Missing columns: " + ", ".join(missing))

    rows, errors = [], []
    try:
        for line_no, rec in enumerate(reader, start=2):
            if not any(v.strip() for v in rec.values() if isinstance(v, str)):
                continue  # blank row
            try:
                rows.append({
                    "line": line_no,
                    "date": parse_date(rec["date"]),
                    "description": (rec["description"] or "").strip(),
                    "amount": parse_amount(rec["amount"]),
                })
            except ValueError as exc:
                errors.append({"line": line_no, "error": str(exc)})
    except csv.Error as exc:
        raise StatementError(f"Could not read CSV: {exc}") from None
    return rows, errors
