"""CSV statement parsing. Handles different headers, date formats, amount styles, sign conventions."""
import csv
import io
from dataclasses import dataclass
from datetime import datetime

from . import rules as R

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%b %d, %Y"]
MAX_ROWS = 5000
DATE_COLS = ["date", "transaction date", "posted date", "post date"]
DESC_COLS = ["description", "merchant", "details", "memo", "name", "payee"]
DEBIT_COLS = ["debit", "withdrawal", "withdrawals"]
CREDIT_COLS = ["credit", "deposit", "deposits"]


class ParseError(ValueError):
    pass


@dataclass
class Row:
    row_num: int
    date: str
    description: str
    amount: float  # negative = money out


def parse_amount(s: str) -> float:
    s = s.strip().replace("$", "").replace(",", "").replace(" ", "")
    if not s:
        raise ValueError("empty amount")
    if s.startswith("(") and s.endswith(")"):
        return -float(s[1:-1])
    return float(s)


def parse_date(s: str) -> str:
    s = s.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date '{s}'")


def _col(headers: dict[str, str], names: list[str]) -> str | None:
    return next((headers[n] for n in names if n in headers), None)


def parse_statement(text: str) -> tuple[list[Row], list[str]]:
    text = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ParseError("File is empty or has no header row")
    headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    date_c, desc_c = _col(headers, DATE_COLS), _col(headers, DESC_COLS)
    amt_c, debit_c, credit_c = headers.get("amount"), _col(headers, DEBIT_COLS), _col(headers, CREDIT_COLS)
    if not date_c or not desc_c or not (amt_c or debit_c or credit_c):
        raise ParseError("Could not find date, description and amount columns")

    rows: list[Row] = []
    warnings: list[str] = []
    for i, rec in enumerate(reader, start=2):
        if len(rows) >= MAX_ROWS:
            warnings.append(f"Stopped after {MAX_ROWS} rows")
            break
        if not any((v or "").strip() for v in rec.values()):
            continue
        try:
            date = parse_date(rec[date_c] or "")
            if amt_c:
                amount = parse_amount(rec[amt_c] or "")
            else:  # separate debit/credit columns: debit = out
                d, c = (rec.get(debit_c) or "").strip(), (rec.get(credit_c) or "").strip()
                amount = (parse_amount(c) if c else 0.0) - (parse_amount(d) if d else 0.0)
            desc = (rec[desc_c] or "").strip()
            if not desc:
                raise ValueError("empty description")
        except (ValueError, TypeError) as e:
            warnings.append(f"Row {i} skipped: {e}")
            continue
        rows.append(Row(i, date, desc, amount))

    if not rows:
        raise ParseError("No valid transactions found")
    if amt_c:
        warnings += _fix_sign_convention(rows)
    return rows, warnings


def _fix_sign_convention(rows: list[Row]) -> list[str]:
    """Banks differ: some export spending as negative, some as positive. Infer from card-payment rows."""
    from .brain import normalize
    pays = [r for r in rows if R.PAYMENT_RE.search(normalize(r.description))]
    flip = False
    if pays:
        flip = sum(r.amount < 0 for r in pays) > len(pays) / 2  # payments are money-in, so negative => flipped
    elif sum(r.amount > 0 for r in rows) / len(rows) >= 0.9:
        flip = True
    if flip:
        for r in rows:
            r.amount = -r.amount
        return ["Detected that this file lists spending as positive numbers; signs were flipped."]
    if not pays:
        return ["Assumed negative amounts are money out (no card-payment row to confirm)."]
    return []
