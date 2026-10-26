"""Turn a CSV bank/credit-card statement into clean Transaction objects.

Convention after parsing: negative amount = money out, positive = money in.
"""
import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%d/%m/%Y"]

# Accepted header names for each field (compared in lowercase).
ALIASES = {
    "date": ["date", "posted date", "transaction date", "post date"],
    "description": ["description", "merchant", "details", "memo", "payee"],
    "amount": ["amount"],
    "debit": ["debit", "withdrawal", "withdrawals"],
    "credit": ["credit", "deposit", "deposits"],
}


class ParseError(ValueError):
    """Raised when a file or a single row cannot be read."""


@dataclass
class Transaction:
    row: int            # line number in the file (so the user can find it)
    date: str           # ISO format: YYYY-MM-DD
    description: str
    amount: Decimal     # negative = money out, positive = money in


def parse_amount(raw: str) -> Decimal:
    s = (raw or "").strip()
    if not s:
        raise ParseError("empty amount")
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = s.replace("$", "").replace(",", "").replace(" ", "")
    if s.endswith("-"):          # some banks write 45.00-
        negative = True
        s = s[:-1]
    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ParseError(f"bad amount: {raw!r}")
    if not value.is_finite():    # Decimal("NaN") would otherwise slip through
        raise ParseError(f"bad amount: {raw!r}")
    return -abs(value) if negative else value


def parse_date(raw: str) -> str:
    text = (raw or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise ParseError(f"bad date: {raw!r}")


def _find_column(headers, key):
    for h in headers:
        if h and h.strip().lower() in ALIASES[key]:
            return h
    return None


def parse_statement(content: bytes, charges_positive: bool = False):
    """Return (transactions, skipped).

    charges_positive=True is for credit-card files that list purchases as
    positive numbers: we flip the sign so purchases become negative.
    """
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []

    date_col = _find_column(headers, "date")
    desc_col = _find_column(headers, "description")
    amount_col = _find_column(headers, "amount")
    debit_col = _find_column(headers, "debit")
    credit_col = _find_column(headers, "credit")

    if not (date_col and desc_col and (amount_col or debit_col or credit_col)):
        raise ParseError(
            "Could not find date, description and amount columns. "
            "Expected headers like: Date, Description, Amount."
        )

    transactions, skipped = [], []
    for row in reader:
        line = reader.line_num
        # Ignore rows that are completely empty (e.g. ",,,").
        if not any((v or "").strip() for v in row.values() if isinstance(v, str) or v is None):
            continue
        try:
            description = (row.get(desc_col) or "").strip()
            if not description:
                raise ParseError("empty description")

            if amount_col:
                amount = parse_amount(row.get(amount_col))
                if charges_positive:
                    amount = -amount
            else:
                out_raw = (row.get(debit_col) or "").strip() if debit_col else ""
                in_raw = (row.get(credit_col) or "").strip() if credit_col else ""
                if not out_raw and not in_raw:
                    raise ParseError("empty amount")
                out = abs(parse_amount(out_raw)) if out_raw else Decimal(0)
                inn = abs(parse_amount(in_raw)) if in_raw else Decimal(0)
                amount = inn - out

            transactions.append(
                Transaction(line, parse_date(row.get(date_col)), description, amount)
            )
        except ParseError as e:
            skipped.append({"row": line, "error": str(e),
                            "raw": {k: v for k, v in row.items() if k}})
    return transactions, skipped