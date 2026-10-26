"""CSV statement parser: turns messy bank / credit-card CSV into Transaction objects.

Amount convention (credit-card statements):
  positive = charge (money out), negative = payment / refund / credit (money in).
Malformed rows are flagged in Transaction.errors instead of raising.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
from decimal import Decimal

from app.models import Transaction

_UNAMBIGUOUS_DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%d-%b-%Y", "%d %b %Y", "%d-%b-%y",
    "%b %d, %Y", "%B %d, %Y", "%d %B %Y", "%d.%m.%Y",
]
_MONTH_FIRST = ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y"]
_DAY_FIRST = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"]

_SYMBOLS = {"$": "USD", "\u20ac": "EUR", "\u00a3": "GBP"}
_CODE_RE = re.compile(r"(?<![A-Za-z])([A-Za-z]{3})(?![A-Za-z])")
_CR_RE = re.compile(r"(?<![A-Za-z])CR(?![A-Za-z])", re.IGNORECASE)
_DR_RE = re.compile(r"(?<![A-Za-z])DR(?![A-Za-z])", re.IGNORECASE)

_ALIASES = {
    "date": {"date", "transaction date", "posted date", "post date", "trans date", "posting date"},
    "description": {"description", "details", "merchant", "memo", "payee", "narrative", "transaction description"},
    "amount": {"amount", "amt", "value"},
    "debit": {"debit", "withdrawal", "withdrawals"},
    "credit": {"credit", "deposit", "deposits"},
    "currency": {"currency", "ccy"},
}


def parse_date(value: str, dayfirst: bool = False) -> dt.date:
    """Parse many date formats. Ambiguous 03/04/2026 is month-first unless dayfirst=True."""
    text = " ".join(value.split())
    if not text:
        raise ValueError("missing date")
    ambiguous = _DAY_FIRST + _MONTH_FIRST if dayfirst else _MONTH_FIRST + _DAY_FIRST
    for fmt in _UNAMBIGUOUS_DATE_FORMATS + ambiguous:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"invalid date: {value!r}")


def parse_amount(value: str) -> tuple[Decimal, str | None]:
    """Return (signed amount, currency hint). Handles 1,234.50 / (50.00) / 25.00 CR / EUR 1.234,50."""
    text = value.strip()
    if not text:
        raise ValueError("missing amount")
    currency: str | None = None
    negative = False

    for symbol, code in _SYMBOLS.items():
        if symbol in text:
            currency = code
            text = text.replace(symbol, "")
    if _CR_RE.search(text):
        negative = True
        text = _CR_RE.sub("", text)
    elif _DR_RE.search(text):
        text = _DR_RE.sub("", text)
    match = _CODE_RE.search(text)
    if match:
        currency = match.group(1).upper()
        text = text[: match.start()] + text[match.end():]

    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    if text.startswith("-") or text.endswith("-"):
        negative = True
        text = text.strip("-").strip()
    text = text.lstrip("+").replace(" ", "")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if re.fullmatch(r"\d+,\d{2}", text):
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

    if not re.fullmatch(r"\d+(\.\d+)?|\.\d+", text):
        raise ValueError(f"invalid amount: {value!r}")
    number = Decimal(text)
    return (-number if negative else number), currency


def _map_columns(fieldnames: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for name in fieldnames:
        key = (name or "").strip().lower()
        for canonical, aliases in _ALIASES.items():
            if key in aliases and canonical not in mapping:
                mapping[canonical] = name
    return mapping


def _detect_delimiter(header_line: str) -> str:
    counts = {d: header_line.count(d) for d in (",", ";", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 0 else ","


def _amount_from_cells(cells: dict[str, str], columns: dict[str, str]) -> tuple[Decimal, str | None]:
    if "amount" in columns:
        raw = cells.get(columns["amount"], "")
        if raw:
            return parse_amount(raw)
    debit_raw = cells.get(columns["debit"], "") if "debit" in columns else ""
    credit_raw = cells.get(columns["credit"], "") if "credit" in columns else ""
    if debit_raw or credit_raw:
        total = Decimal("0")
        hint: str | None = None
        if debit_raw:
            value, hint = parse_amount(debit_raw)
            total += abs(value)
        if credit_raw:
            value, credit_hint = parse_amount(credit_raw)
            total -= abs(value)
            hint = hint or credit_hint
        return total, hint
    raise ValueError("missing amount")


def parse_csv(content: bytes | str, dayfirst: bool = False) -> list[Transaction]:
    """Parse CSV text/bytes into Transactions. Empty rows are skipped, bad rows are flagged."""
    if isinstance(content, bytes):
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content.lstrip("\ufeff")
    text = text.lstrip()
    if not text:
        raise ValueError("CSV file is empty")

    reader = csv.DictReader(io.StringIO(text), delimiter=_detect_delimiter(text.splitlines()[0]))
    columns = _map_columns(list(reader.fieldnames or []))
    missing = [name for name in ("date", "description") if name not in columns]
    if not ({"amount", "debit", "credit"} & set(columns)):
        missing.append("amount")
    if missing:
        raise ValueError("CSV is missing required column(s): " + ", ".join(missing))

    transactions: list[Transaction] = []
    for row in reader:
        extra = row.pop(None, None)
        cells = {key: (value or "").strip() for key, value in row.items()}
        if not any(cells.values()) and not extra:
            continue

        errors: list[str] = []
        txn_date: dt.date | None = None
        try:
            txn_date = parse_date(cells.get(columns["date"], ""), dayfirst)
        except ValueError as exc:
            errors.append(str(exc))

        description = " ".join(cells.get(columns["description"], "").split())
        if not description:
            errors.append("missing description")

        amount: Decimal | None = None
        hint: str | None = None
        try:
            amount, hint = _amount_from_cells(cells, columns)
        except ValueError as exc:
            errors.append(str(exc))

        currency_cell = cells.get(columns["currency"], "") if "currency" in columns else ""
        if currency_cell and not re.fullmatch(r"[A-Za-z]{3}", currency_cell):
            errors.append(f"invalid currency: {currency_cell!r}")
            currency_cell = ""
        if extra:
            errors.append("row has more columns than the header")

        transactions.append(
            Transaction(
                row_number=reader.line_num,
                txn_date=txn_date,
                description=description,
                amount=amount,
                currency=(currency_cell or hint or "USD").upper(),
                raw=cells,
                errors=errors,
            )
        )
    return transactions
