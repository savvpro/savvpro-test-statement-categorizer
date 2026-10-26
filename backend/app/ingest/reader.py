"""Read a bank or credit-card export into clean, signed transactions.

Handles the mess real exports contain: preamble lines before the header, no header at
all, BOMs and Windows encodings, ``;``/tab delimiters, separate debit/credit columns,
pending rows, summary/total rows, zero-amount holds, and both sign conventions
(spending shown as negative by most banks, as positive by many card issuers).
OFX/QFX (Quicken / "Web Connect") files are supported too.
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from .values import (
    detect_date_format,
    looks_like_amount,
    looks_like_date,
    parse_amount,
    try_parse_date,
)


class SignConvention(StrEnum):
    AUTO = "auto"
    NEGATIVE_IS_SPENDING = "negative_is_spending"  # most bank accounts
    POSITIVE_IS_SPENDING = "positive_is_spending"  # many credit-card exports


class StatementParseError(ValueError):
    """The file cannot be read as a statement. The message is safe to show to users."""


@dataclass(frozen=True, slots=True)
class RawTransaction:
    line: int
    date: date
    description: str
    amount: Decimal  # signed from the user's point of view: + money in, - money out
    bank_category: str | None = None


@dataclass(frozen=True, slots=True)
class SkippedRow:
    line: int
    reason: str
    content: str


@dataclass(slots=True)
class ParsedStatement:
    transactions: list[RawTransaction]
    skipped: list[SkippedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sign_convention: SignConvention = SignConvention.NEGATIVE_IS_SPENDING
    file_format: str = "csv"


# ----------------------------------------------------------------------- columns
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "date": (
        "transaction date",
        "trans date",
        "date",
        "posted date",
        "post date",
        "posting date",
        "date posted",
        "booking date",
        "value date",
    ),
    "description": (
        "description",
        "transaction description",
        "merchant",
        "merchant name",
        "payee",
        "name",
        "details",
        "transaction details",
        "narrative",
        "original description",
    ),
    "memo": ("memo", "extended details", "additional info", "reference"),
    "amount": ("amount", "transaction amount", "amount usd", "amount (usd)", "value"),
    "debit": (
        "debit",
        "debits",
        "withdrawal",
        "withdrawals",
        "debit amount",
        "money out",
        "charges",
        "paid out",
    ),
    "credit": (
        "credit",
        "credits",
        "deposit",
        "deposits",
        "credit amount",
        "money in",
        "payments",
        "paid in",
    ),
    "type": ("type", "transaction type", "dr/cr", "debit/credit", "credit/debit", "cr/dr"),
    "category": ("category", "bank category", "merchant category"),
    "status": ("status", "transaction status"),
}

_SUMMARY_ROW = re.compile(r"\b(?:TOTAL|BALANCE|OPENING|CLOSING|BEGINNING|ENDING|SUMMARY)\b", re.I)
_CARD_PAYMENT = re.compile(
    r"PAYMENT\s*-?\s*THANK YOU|THANK YOU FOR YOUR PAYMENT|AUTOPAY PAYMENT", re.I
)
_MAX_PREAMBLE = 25


def _norm_header(cell: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/() ]", " ", cell.lower())).strip()


def _map_header(cells: list[str]) -> dict[str, int] | None:
    normalized = [_norm_header(c) for c in cells]
    mapping: dict[str, int] = {}
    for field_name, aliases in COLUMN_ALIASES.items():
        # Aliases are in preference order, e.g. "transaction date" beats "post date".
        for alias in aliases:
            if alias in normalized and normalized.index(alias) not in mapping.values():
                mapping[field_name] = normalized.index(alias)
                break
    has_money = "amount" in mapping or ("debit" in mapping or "credit" in mapping)
    if "date" in mapping and "description" in mapping and has_money:
        return mapping
    return None


def _infer_columns(rows: list[list[str]]) -> dict[str, int] | None:
    """For header-less exports: find date, amount and description columns from the data."""
    sample = [r for r in rows if any(c.strip() for c in r)][:50]
    if not sample:
        return None
    width = max(len(r) for r in sample)

    def share(col: int, test) -> float:
        cells = [r[col] for r in sample if col < len(r) and r[col].strip()]
        return sum(1 for c in cells if test(c)) / len(sample) if cells else 0.0

    date_col = next((c for c in range(width) if share(c, looks_like_date) >= 0.8), None)
    if date_col is None:
        return None
    amount_col = next(
        (c for c in range(width) if c != date_col and share(c, looks_like_amount) >= 0.8), None
    )
    if amount_col is None:
        return None

    def avg_text(col: int) -> float:
        cells = [r[col] for r in sample if col < len(r)]
        return sum(len(c) for c in cells if not looks_like_amount(c)) / len(sample)

    others = [c for c in range(width) if c not in (date_col, amount_col)]
    if not others:
        return None
    desc_col = max(others, key=avg_text)
    if avg_text(desc_col) < 3:
        return None
    return {"date": date_col, "amount": amount_col, "description": desc_col}


# ----------------------------------------------------------------------- decoding
def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _sniff_delimiter(text: str) -> str:
    """Pick the delimiter that splits the most lines into the same number of columns.

    ``csv.Sniffer`` gives up on files whose preamble lines have fewer columns than the
    data, which is exactly what many bank exports look like.
    """
    lines = [re.sub(r'"[^"]*"', "", ln) for ln in text.splitlines()[:60] if ln.strip()]
    best, best_score = ",", 0
    for delimiter in (",", ";", "\t", "|"):
        counts = Counter(ln.count(delimiter) for ln in lines)
        counts.pop(0, None)
        if counts:
            score = counts.most_common(1)[0][1]
            if score > best_score:
                best, best_score = delimiter, score
    return best


# ----------------------------------------------------------------------- public API
def read_statement(
    data: bytes, *, sign_convention: SignConvention = SignConvention.AUTO
) -> ParsedStatement:
    if not data or not data.strip():
        raise StatementParseError("The file is empty.")
    text = _decode(data)
    if "<OFX>" in text.upper() or "<STMTTRN>" in text.upper():
        return _read_ofx(text)
    return _read_csv(text, sign_convention)


def _read_csv(text: str, sign_convention: SignConvention) -> ParsedStatement:
    reader = csv.reader(io.StringIO(text), delimiter=_sniff_delimiter(text))
    rows: list[tuple[int, list[str]]] = []
    for row in reader:
        rows.append((reader.line_num, [c.strip() for c in row]))
    if not rows:
        raise StatementParseError("The file has no rows.")

    header_index, mapping = None, None
    for i, (_, cells) in enumerate(rows[:_MAX_PREAMBLE]):
        if mapping := _map_header(cells):
            header_index = i
            break
    warnings: list[str] = []
    if mapping is None:
        mapping = _infer_columns([cells for _, cells in rows])
        if mapping is None:
            raise StatementParseError(
                "Could not find the transaction columns. Expected a header such as "
                "'Date, Description, Amount' (or Debit/Credit columns)."
            )
        warnings.append("No header row found; columns were detected from the data.")
        body = rows
    else:
        body = rows[header_index + 1 :]
        if header_index:
            warnings.append(f"Skipped {header_index} line(s) of account info above the header.")

    def cell(cells: list[str], name: str) -> str:
        idx = mapping.get(name)
        return cells[idx] if idx is not None and idx < len(cells) else ""

    date_format, date_warnings = detect_date_format(cell(c, "date") for _, c in body)
    warnings.extend(date_warnings)
    if date_format is None:
        raise StatementParseError("Could not recognise the date format in the date column.")

    transactions: list[RawTransaction] = []
    skipped: list[SkippedRow] = []
    type_column_used = False

    for line, cells in body:
        if not any(cells):
            continue
        content = ", ".join(c for c in cells if c)[:200]
        description = cell(cells, "description")
        memo = cell(cells, "memo")
        if memo and memo.upper() not in description.upper():
            description = f"{description} {memo}".strip()

        if cell(cells, "status").lower() in {"pending", "pend", "authorized", "authorised"}:
            skipped.append(
                SkippedRow(line, "Pending - it will be categorised once it posts.", content)
            )
            continue

        raw_date = cell(cells, "date")
        tx_date = try_parse_date(raw_date, date_format) if raw_date else None
        if tx_date is None:
            reason = (
                "Summary or balance line, not a transaction."
                if _SUMMARY_ROW.search(content) or not raw_date
                else f"Could not read the date '{raw_date}'."
            )
            skipped.append(SkippedRow(line, reason, content))
            continue

        try:
            amount, used_type = _row_amount(cells, mapping, cell)
        except ValueError as exc:
            skipped.append(SkippedRow(line, str(exc), content))
            continue
        type_column_used |= used_type
        if amount == 0:
            skipped.append(
                SkippedRow(line, "Zero amount (card authorisation or memo line).", content)
            )
            continue

        transactions.append(
            RawTransaction(
                line=line,
                date=tx_date,
                description=description or "(no description)",
                amount=amount,
                bank_category=cell(cells, "category") or None,
            )
        )

    if not transactions:
        raise StatementParseError("No transactions were found in the file.")

    has_explicit_direction = type_column_used or "amount" not in mapping
    convention = sign_convention
    if has_explicit_direction:
        convention = SignConvention.NEGATIVE_IS_SPENDING
    elif convention is SignConvention.AUTO:
        convention, why = _detect_sign_convention(transactions)
        warnings.append(why)
    if convention is SignConvention.POSITIVE_IS_SPENDING:
        transactions = [
            RawTransaction(t.line, t.date, t.description, -t.amount, t.bank_category)
            for t in transactions
        ]

    return ParsedStatement(
        transactions=transactions,
        skipped=skipped,
        warnings=warnings,
        sign_convention=convention,
        file_format="csv",
    )


def _row_amount(cells, mapping, cell) -> tuple[Decimal, bool]:
    """Return the signed amount (+ in / - out) as the file states it."""
    if "amount" in mapping:
        amount = parse_amount(cell(cells, "amount"))
        if amount is None:
            raise ValueError("No amount on this row.")
        kind = cell(cells, "type").strip().lower()
        if kind in {"debit", "dr", "d", "withdrawal", "sale", "purchase", "fee"}:
            return -abs(amount), True
        if kind in {"credit", "cr", "c", "deposit", "return", "refund", "payment"}:
            return abs(amount), True
        return amount, False

    debit = parse_amount(cell(cells, "debit"))
    credit = parse_amount(cell(cells, "credit"))
    if debit is None and credit is None:
        raise ValueError("No amount on this row.")
    return abs(credit or Decimal(0)) - abs(debit or Decimal(0)), True


def _detect_sign_convention(transactions: list[RawTransaction]) -> tuple[SignConvention, str]:
    payments = [t for t in transactions if _CARD_PAYMENT.search(t.description)]
    if payments:
        # A card payment is money *into* the card account.
        if sum(1 for t in payments if t.amount < 0) > len(payments) / 2:
            return (
                SignConvention.POSITIVE_IS_SPENDING,
                "Detected a credit-card export (charges positive, payments negative).",
            )
        return (
            SignConvention.NEGATIVE_IS_SPENDING,
            "Detected spending shown as negative amounts.",
        )
    positives = sum(1 for t in transactions if t.amount > 0)
    if positives > len(transactions) / 2:
        return (
            SignConvention.POSITIVE_IS_SPENDING,
            "Most amounts are positive, so positive amounts were read as spending. "
            "If that is wrong, re-upload and choose the sign convention.",
        )
    return SignConvention.NEGATIVE_IS_SPENDING, "Detected spending shown as negative amounts."


# ----------------------------------------------------------------------- OFX / QFX
_OFX_TXN = re.compile(
    r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|(?=</BANKTRANLIST>))", re.S | re.I
)


def _ofx_field(block: str, name: str) -> str:
    m = re.search(rf"<{name}>([^<\r\n]*)", block, re.I)
    return m.group(1).strip() if m else ""


def _read_ofx(text: str) -> ParsedStatement:
    transactions: list[RawTransaction] = []
    skipped: list[SkippedRow] = []
    for i, m in enumerate(_OFX_TXN.finditer(text), start=1):
        block = m.group(1)
        content = re.sub(r"\s+", " ", block)[:200]
        raw_date = _ofx_field(block, "DTPOSTED")[:8]
        tx_date = try_parse_date(raw_date, "%Y%m%d") if raw_date else None
        try:
            amount = parse_amount(_ofx_field(block, "TRNAMT"))
        except ValueError:
            amount = None
        if tx_date is None or amount is None:
            skipped.append(SkippedRow(i, "Missing date or amount.", content))
            continue
        if amount == 0:
            skipped.append(SkippedRow(i, "Zero amount.", content))
            continue
        name, memo = _ofx_field(block, "NAME"), _ofx_field(block, "MEMO")
        description = (
            f"{name} {memo}".strip() if memo and memo.upper() not in name.upper() else name
        )
        transactions.append(
            RawTransaction(i, tx_date, description or memo or "(no description)", amount)
        )
    if not transactions:
        raise StatementParseError("No transactions were found in the OFX file.")
    # OFX amounts are always signed from the account holder's side: no guessing needed.
    return ParsedStatement(
        transactions=transactions,
        skipped=skipped,
        warnings=[],
        sign_convention=SignConvention.NEGATIVE_IS_SPENDING,
        file_format="ofx",
    )
