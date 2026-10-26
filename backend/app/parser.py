"""Reads a CSV statement into clean rows. Bad rows are reported, not fatal."""
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

MAX_ROWS = 5000

COLUMN_ALIASES = {
    "date": ["date", "transaction date", "posting date", "posted date", "trans date"],
    "description": ["description", "details", "merchant", "memo", "narrative",
                    "transaction description", "payee"],
    "amount": ["amount", "transaction amount"],
    "debit": ["debit", "withdrawal", "withdrawals", "money out"],
    "credit": ["credit", "deposit", "deposits", "money in"],
}
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%d/%m/%y",
                "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"]


class StatementError(Exception):
    """The whole file cannot be used (empty, wrong columns, too big)."""


@dataclass
class ParsedRow:
    row_number: int
    date: str  # ISO yyyy-mm-dd
    description: str
    amount: Decimal  # negative = money out, positive = money in


@dataclass
class ParseResult:
    rows: List[ParsedRow] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise StatementError("Could not read the file text.")


def _map_columns(headers: List[str]) -> Dict[str, str]:
    lowered = {h.strip().lower(): h for h in headers if h}
    mapping = {}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lowered:
                mapping[key] = lowered[alias]
                break
    return mapping


def parse_amount(value: Optional[str]) -> Optional[Decimal]:
    """'$1,234.50' -> 1234.50, '(20.00)' -> -20.00, '' -> None."""
    if value is None or not value.strip():
        return None
    text = value.strip().replace("$", "").replace(",", "").replace(" ", "")
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"'{value}' is not a valid amount")
    return -number if negative else number


def _detect_date_format(values: List[str]) -> Optional[str]:
    """Pick the format that parses the most dates (fixes day/month mix-ups)."""
    best, best_score = None, 0
    for fmt in DATE_FORMATS:
        score = 0
        for v in values:
            try:
                datetime.strptime(v.strip(), fmt)
                score += 1
            except ValueError:
                pass
        if score > best_score:
            best, best_score = fmt, score
    return best


def parse_statement(raw: bytes, charges_are_positive: bool = True) -> ParseResult:
    if not raw.strip():
        raise StatementError("The file is empty.")
    text = _decode(raw)
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise StatementError("The file has no header row.")

    cols = _map_columns(reader.fieldnames)
    missing = [c for c in ("date", "description") if c not in cols]
    if "amount" not in cols and not ("debit" in cols or "credit" in cols):
        missing.append("amount (or debit/credit)")
    if missing:
        raise StatementError(
            "Missing column(s): " + ", ".join(missing)
            + ". Found: " + ", ".join(reader.fieldnames)
        )

    records = list(reader)
    if len(records) > MAX_ROWS:
        raise StatementError(f"Too many rows (limit {MAX_ROWS}).")
    if not records:
        raise StatementError("The file has headers but no transactions.")

    date_format = _detect_date_format(
        [r.get(cols["date"]) or "" for r in records if (r.get(cols["date"]) or "").strip()]
    )

    result = ParseResult()
    for index, record in enumerate(records, start=2):  # row 1 is the header
        try:
            date_text = (record.get(cols["date"]) or "").strip()
            description = (record.get(cols["description"]) or "").strip()
            if not date_text and not description:
                continue  # blank line
            if not date_format:
                raise ValueError("no readable dates in this file")
            try:
                date = datetime.strptime(date_text, date_format).date().isoformat()
            except ValueError:
                raise ValueError(f"'{date_text}' is not a valid date")
            amount = _row_amount(record, cols, charges_are_positive)
            result.rows.append(ParsedRow(index, date, description, amount))
        except ValueError as error:
            result.errors.append({"row_number": index, "reason": str(error)})
    if not result.rows:
        raise StatementError("No usable rows found. " + "; ".join(
            f"row {e['row_number']}: {e['reason']}" for e in result.errors[:3]))
    return result


def _row_amount(record, cols, charges_are_positive) -> Decimal:
    if "debit" in cols or "credit" in cols:
        debit = parse_amount(record.get(cols.get("debit", ""), None))
        credit = parse_amount(record.get(cols.get("credit", ""), None))
        if debit is None and credit is None:
            raise ValueError("no amount")
        return (credit or Decimal(0)) - abs(debit or Decimal(0))
    value = parse_amount(record.get(cols["amount"]))
    if value is None:
        raise ValueError("no amount")
    return -value if charges_are_positive else value
