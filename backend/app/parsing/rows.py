"""Turn raw rows from any parser into clean, signed transactions.

CSV, PDF and OCR parsers all produce RawRow objects. This module applies the
same checks to all of them, so a scanned statement is held to the same rules
as a CSV file.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .values import (
    AUTO,
    NeedsUserChoice,
    ValueProblem,
    currency_from_text,
    normalize_description,
    parse_amount,
    parse_date,
    resolve_date_order,
)

OCR_CONFIDENCE_FLOOR = 80  # tesseract word confidence, 0-100


@dataclass
class RawRow:
    source_row: str  # "row 7" for CSV, "page 2, line 14" for PDF
    date_text: str = ""
    description: str = ""
    amount_text: str = ""
    debit_text: str = ""
    credit_text: str = ""
    balance_text: str = ""
    type_text: str = ""  # DR / CR column, when a bank uses one
    currency_text: str = ""
    ocr_confidence: float | None = None


@dataclass
class ParsedFile:
    rows: list[RawRow]
    source_kind: str  # csv | pdf | ocr
    has_balance: bool = False
    currency_hint: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class Issue:
    source_row: str
    text: str
    reason: str


@dataclass
class CleanRow:
    source_row: str
    txn_date: date
    description: str
    amount: Decimal  # positive = money in, negative = money out
    currency: str
    balance: Decimal | None = None
    flags: list[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        return f"{self.txn_date.isoformat()}|{self.currency}|{self.amount}|{normalize_description(self.description)}"


@dataclass
class CleanResult:
    rows: list[CleanRow]
    skipped: list[Issue]
    errors: list[Issue]
    warnings: list[str]
    currency: str


_SKIP_LINES = re.compile(
    r"\b(OPENING BALANCE|CLOSING BALANCE|BALANCE B/?F|BALANCE C/?F|BROUGHT FORWARD|"
    r"CARRIED FORWARD|BALANCE FORWARD|TOTAL DEBITS?|TOTAL CREDITS?|GRAND TOTAL|SUB ?TOTAL)\b"
)
_OPENING_LINE = re.compile(r"OPENING|B/?F\b|BROUGHT")
_DEBIT_WORDS = {"DR", "D", "DEBIT", "WITHDRAWAL", "OUT"}
_CREDIT_WORDS = {"CR", "C", "CREDIT", "DEPOSIT", "IN"}


def _row_text(raw: RawRow) -> str:
    parts = [raw.date_text, raw.description, raw.amount_text, raw.debit_text, raw.credit_text, raw.balance_text]
    return " | ".join(p for p in parts if p)


def _is_blank(raw: RawRow) -> bool:
    return not any(
        (raw.date_text, raw.description, raw.amount_text, raw.debit_text, raw.credit_text, raw.balance_text)
    )


def _signed_amount(raw: RawRow) -> Decimal:
    if raw.amount_text.strip():
        amount = parse_amount(raw.amount_text)
        kind = raw.type_text.strip().upper()
        if not kind:
            return amount  # documented convention: negative means money out
        if kind in _DEBIT_WORDS:
            return amount if amount < 0 else -amount
        if kind in _CREDIT_WORDS:
            if amount < 0:
                raise ValueProblem("type column says credit but the amount is negative")
            return amount
        raise ValueProblem(f"type '{raw.type_text}' is not DR or CR")

    debit = parse_amount(raw.debit_text) if raw.debit_text.strip() else Decimal(0)
    credit = parse_amount(raw.credit_text) if raw.credit_text.strip() else Decimal(0)
    if debit and credit:
        raise ValueProblem("row has both a debit and a credit")
    if debit:
        return -abs(debit)
    if credit:
        if credit < 0:
            raise ValueProblem("credit column holds a negative number")
        return credit
    if raw.debit_text.strip() or raw.credit_text.strip():
        return Decimal(0)
    raise ValueProblem("row has no amount")


def clean_rows(parsed: ParsedFile, currency_choice: str = AUTO, date_choice: str = AUTO) -> CleanResult:
    skipped: list[Issue] = []
    errors: list[Issue] = []
    warnings: list[str] = list(parsed.notes)
    opening_balance: Decimal | None = None

    candidates: list[RawRow] = []
    for raw in parsed.rows:
        if _is_blank(raw):
            continue
        if _SKIP_LINES.search(raw.description.upper()):
            skipped.append(Issue(raw.source_row, _row_text(raw), "Balance or total line, not a transaction"))
            if _OPENING_LINE.search(raw.description.upper()):
                try:
                    opening_balance = parse_amount(raw.balance_text or raw.amount_text or raw.credit_text)
                except ValueProblem:
                    pass
            continue
        candidates.append(raw)

    # The date format is decided once for the whole file.
    order = resolve_date_order([r.date_text for r in candidates], date_choice)

    # The currency is decided once too, unless the file has a currency column.
    statement_currency = None if currency_choice == AUTO else currency_choice
    file_has_currency = any(r.currency_text.strip() for r in candidates)
    if statement_currency is None and not file_has_currency:
        statement_currency = parsed.currency_hint
    if statement_currency is None and not file_has_currency:
        raise NeedsUserChoice(
            "The app couldn't tell whether this statement is in PKR or USD. "
            "Pick the currency and upload again."
        )

    rows: list[CleanRow] = []
    for raw in candidates:
        try:
            when = parse_date(raw.date_text, order)
            amount = _signed_amount(raw)
            currency = statement_currency
            if raw.currency_text.strip():
                row_currency = currency_from_text(raw.currency_text)
                if statement_currency and row_currency != statement_currency:
                    raise ValueProblem(f"row says {row_currency} but you chose {statement_currency}")
                currency = row_currency
            if not raw.description.strip():
                raise ValueProblem("description is empty")
            balance = parse_amount(raw.balance_text) if raw.balance_text.strip() else None
        except ValueProblem as problem:
            message = str(problem)
            errors.append(Issue(raw.source_row, _row_text(raw), message[:1].upper() + message[1:]))
            continue
        if amount == 0:
            skipped.append(Issue(raw.source_row, _row_text(raw), "Zero amount, information line only"))
            continue
        row = CleanRow(raw.source_row, when, raw.description.strip(), amount, currency, balance)
        if raw.ocr_confidence is not None and raw.ocr_confidence < OCR_CONFIDENCE_FLOOR:
            row.flags.append(
                f"The scanner wasn't sure about this line ({raw.ocr_confidence:.0f}% confident). "
                "Check the date and amount against the statement."
            )
        rows.append(row)

    # Some banks list newest first. Work oldest first so balances and refunds line up.
    if len(rows) > 1 and rows[0].txn_date > rows[-1].txn_date:
        rows.reverse()

    _check_running_balance(rows, opening_balance, warnings)

    if parsed.source_kind == "ocr" and not parsed.has_balance:
        for row in rows:
            row.flags.append("Read from a scanned page with no balance column to check it against.")

    _flag_repeats(rows)

    currencies = {r.currency for r in rows}
    if len(currencies) == 1:
        currency = currencies.pop()
    else:
        currency = "mixed" if currencies else (statement_currency or "unknown")
    return CleanResult(rows, skipped, errors, warnings, currency)


def _check_running_balance(rows: list[CleanRow], opening: Decimal | None, warnings: list[str]) -> None:
    """Each balance should equal the previous balance plus this amount.

    This is the best defence against a misread digit or a lost minus sign,
    especially on scanned statements.
    """
    previous = opening
    checked = mismatched = 0
    for row in rows:
        if row.balance is None:
            previous = None
            continue
        if previous is not None:
            checked += 1
            expected = previous + row.amount
            if expected != row.balance:
                mismatched += 1
                row.flags.append(
                    f"The running balance doesn't add up (expected {expected:,.2f}, the statement shows "
                    f"{row.balance:,.2f}). The amount may have been read wrongly."
                )
        previous = row.balance
    if checked and mismatched / checked > 0.5:
        warnings.append(
            "Most rows don't add up against the running balance. Check that the debit and credit "
            "columns aren't swapped and that money out is negative."
        )


def _flag_repeats(rows: list[CleanRow]) -> None:
    seen: dict[str, str] = {}
    for row in rows:
        key = row.fingerprint
        if key in seen:
            row.flags.append(
                f"Same date, amount and description as {seen[key]} in this file. "
                "It may be a duplicate. Nothing was deleted."
            )
        else:
            seen[key] = row.source_row
