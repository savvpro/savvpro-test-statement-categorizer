"""Read a bank or card CSV export into clean rows.

Banks disagree on almost everything, so this module:
- finds the header row even when the file starts with a preamble,
- maps column names by synonym (Date / Posted Date / Trans. Date ...),
- accepts one signed Amount column or separate Debit / Credit columns,
- parses "$1,234.56", "(12.34)", "12.34-", "12.34 CR" and several date formats,
- works out whether a single Amount column is bank style (money out is
  negative) or card style (purchases positive, payments negative),
- skips blank, total and broken rows and reports why instead of failing.

Every row comes out with `amount` signed from the customer's point of view:
negative = money out, positive = money in.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

SignMode = Literal["auto", "bank", "card"]

DATE_COLS = ("date", "transaction date", "trans. date", "trans date", "posted date", "posting date", "post date")
DESC_COLS = ("description", "merchant", "payee", "details", "memo", "name", "transaction description")
AMOUNT_COLS = ("amount", "transaction amount", "amount (usd)")
DEBIT_COLS = ("debit", "withdrawal", "withdrawals", "money out", "charges")
CREDIT_COLS = ("credit", "deposit", "deposits", "money in", "payments")
STATUS_COLS = ("status",)
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%Y", "%b %d, %Y", "%m-%d-%Y")
CARD_PAYMENT_HINT = re.compile(r"PAYMENT\s*(-\s*)?THANK\s*YOU|CREDIT CARD PAYMENT", re.I)


class StatementError(ValueError):
    """The file cannot be read as a statement at all."""


@dataclass
class RawTransaction:
    row: int
    date: date
    description: str
    amount: Decimal
    pending: bool = False


@dataclass
class ParseResult:
    transactions: list[RawTransaction] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    sign_mode: str = "bank"
    columns: dict[str, str] = field(default_factory=dict)


def parse_amount(text: str) -> Decimal | None:
    s = (text or "").strip().upper()
    if not s:
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative, s = True, s[1:-1]
    if s.endswith("CR"):
        s = s[:-2].strip()
    elif s.endswith("DR"):
        negative, s = True, s[:-2].strip()
    if s.endswith("-"):
        negative, s = True, s[:-1]
    if s.startswith("-"):
        negative, s = not negative, s[1:]
    s = s.replace("$", "").replace(",", "").replace(" ", "").replace("USD", "")
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return -value if negative else value


def parse_date(text: str) -> date | None:
    s = (text or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _find(header: list[str], names: tuple[str, ...]) -> int | None:
    norm = [h.strip().lower() for h in header]
    for name in names:
        if name in norm:
            return norm.index(name)
    return None


def _find_header(rows: list[list[str]]) -> int:
    for i, row in enumerate(rows[:15]):
        if _find(row, DATE_COLS) is not None and _find(row, DESC_COLS) is not None:
            return i
    raise StatementError("Could not find a header row with a date and a description column.")


def parse_csv(content: bytes, sign: SignMode = "auto") -> ParseResult:
    text = content.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise StatementError("The file is empty.")
    h = _find_header(rows)
    header = rows[h]
    cols = {
        "date": _find(header, DATE_COLS),
        "description": _find(header, DESC_COLS),
        "amount": _find(header, AMOUNT_COLS),
        "debit": _find(header, DEBIT_COLS),
        "credit": _find(header, CREDIT_COLS),
        "status": _find(header, STATUS_COLS),
    }
    split = cols["debit"] is not None and cols["credit"] is not None
    if cols["amount"] is None and not split:
        raise StatementError("Could not find an Amount column or Debit/Credit columns.")

    result = ParseResult(columns={k: header[v] for k, v in cols.items() if v is not None})
    pending_rows: list[tuple[int, list[str]]] = []
    for line_no, row in enumerate(rows[h + 1 :], start=h + 2):
        if not any(cell.strip() for cell in row):
            continue
        pending_rows.append((line_no, row))

    def cell(row: list[str], key: str) -> str:
        i = cols[key]
        return row[i] if i is not None and i < len(row) else ""

    parsed: list[tuple[int, date, str, Decimal, bool]] = []
    for line_no, row in pending_rows:
        desc = " ".join(cell(row, "description").split())
        if desc.lower().startswith(("total", "ending balance", "beginning balance")):
            result.skipped.append({"row": line_no, "reason": "Summary line, not a transaction"})
            continue
        when = parse_date(cell(row, "date"))
        if when is None:
            result.skipped.append({"row": line_no, "reason": f"Unreadable date '{cell(row, 'date')}'"})
            continue
        if not desc:
            result.skipped.append({"row": line_no, "reason": "No description"})
            continue
        if split:
            debit, credit = parse_amount(cell(row, "debit")), parse_amount(cell(row, "credit"))
            if debit is None and credit is None:
                result.skipped.append({"row": line_no, "reason": "No amount"})
                continue
            amount = (credit or Decimal(0)).copy_abs() - (debit or Decimal(0)).copy_abs()
        else:
            amount = parse_amount(cell(row, "amount"))
            if amount is None:
                result.skipped.append({"row": line_no, "reason": f"Unreadable amount '{cell(row, 'amount')}'"})
                continue
        if amount == 0:
            result.skipped.append({"row": line_no, "reason": "Zero amount (authorization hold)"})
            continue
        status = cell(row, "status").strip().lower()
        parsed.append((line_no, when, desc, amount, status == "pending"))

    mode = sign
    if not split and sign == "auto":
        # Card exports list the payment you made to the card as negative and
        # purchases as positive. If the payment rows are negative, flip.
        # A bill paid on autopay looks similar, so also require that most
        # other rows (the purchases) are positive.
        hints = [a for _, _, d, a, _ in parsed if CARD_PAYMENT_HINT.search(d)]
        others = [a for _, _, d, a, _ in parsed if not CARD_PAYMENT_HINT.search(d)]
        mostly_positive = sum(a > 0 for a in others) > len(others) / 2
        mode = "card" if hints and all(a < 0 for a in hints) and mostly_positive else "bank"
    elif split:
        mode = "bank"
    result.sign_mode = mode
    for line_no, when, desc, amount, pending in parsed:
        signed = -amount if (mode == "card" and not split) else amount
        result.transactions.append(RawTransaction(line_no, when, desc, signed, pending))
    if not result.transactions:
        raise StatementError("No transactions found in the file.")
    return result
