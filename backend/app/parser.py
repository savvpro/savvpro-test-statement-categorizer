"""Reads a CSV bank/credit-card statement into signed RawTransactions.

Statements are messy: column names differ, dates can be d/m or m/d, amounts
can be "(45.00)", "$1,200.00" or "45.00 CR", and some exports split money
in/out into two columns. Rows we cannot trust are reported, never guessed.
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .models import ParseIssue, RawTransaction

MAX_ROWS = 5000

DATE_COLUMNS = ("date", "transaction date", "trans date", "posted date", "post date", "posting date")
DESC_COLUMNS = ("description", "details", "memo", "merchant", "payee", "name", "narrative")
AMOUNT_COLUMNS = ("amount", "amt", "transaction amount")
DEBIT_COLUMNS = ("debit", "withdrawal", "withdrawals", "money out", "paid out")
CREDIT_COLUMNS = ("credit", "deposit", "deposits", "money in", "paid in")

SUMMARY_ROW = re.compile(r"^(total|opening balance|closing balance|balance|statement total)\b", re.I)

NAMED_DATE_FORMATS = ("%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%B %d, %Y", "%Y/%m/%d")


@dataclass
class ParseResult:
    transactions: list[RawTransaction] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class StatementError(ValueError):
    """The file as a whole cannot be used (not a readable statement)."""


def decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise StatementError("File is not readable text. Please upload a CSV export.")


def _find(headers: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in headers:
            return headers[candidate]
    return None


def parse_amount(text: str) -> Decimal:
    """Returns a signed amount as written (negative = parentheses, minus or DR)."""
    value = text.strip().replace("−", "-")
    if not value:
        raise ValueError("empty amount")
    negative = False
    upper = value.upper()
    if upper.endswith("CR"):
        value = value[:-2]
    elif upper.endswith("DR"):
        value, negative = value[:-2], True
    value = value.strip()
    if value.startswith("(") and value.endswith(")"):
        value, negative = value[1:-1], True
    value = re.sub(r"[£$€\s,]", "", value)
    if value.startswith("-"):
        value, negative = value[1:], not negative
    elif value.startswith("+"):
        value = value[1:]
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"cannot read amount {text!r}") from None
    if not number.is_finite():
        raise ValueError(f"cannot read amount {text!r}")
    return -number if negative else number


def _slash_order(values: list[str]) -> tuple[str, bool]:
    """Decides d/m vs m/d for the whole file. Returns (format order, was_ambiguous)."""
    first_over_12 = second_over_12 = False
    for value in values:
        match = re.match(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-]\d{2,4}$", value.strip())
        if match:
            first_over_12 |= int(match.group(1)) > 12
            second_over_12 |= int(match.group(2)) > 12
    if first_over_12 and not second_over_12:
        return "dmy", False
    if second_over_12 and not first_over_12:
        return "mdy", False
    return "mdy", not (first_over_12 or second_over_12)


def parse_date(text: str, order: str) -> date:
    value = text.strip()
    for fmt in NAMED_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    match = re.match(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})$", value)
    if match:
        a, b, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000
        day, month = (a, b) if order == "dmy" else (b, a)
        try:
            return date(year, month, day)
        except ValueError:
            pass
    raise ValueError(f"cannot read date {text!r}")


def parse_statement(content: bytes, positive_is_charge: bool = False) -> ParseResult:
    """positive_is_charge: card exports often list purchases as positive numbers."""
    text = decode(content)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise StatementError("The file is empty.")

    headers = {name.strip().lower(): name for name in reader.fieldnames if name}
    date_col = _find(headers, DATE_COLUMNS)
    desc_col = _find(headers, DESC_COLUMNS)
    amount_col = _find(headers, AMOUNT_COLUMNS)
    debit_col = _find(headers, DEBIT_COLUMNS)
    credit_col = _find(headers, CREDIT_COLUMNS)
    if not date_col or not desc_col or not (amount_col or debit_col or credit_col):
        raise StatementError(
            "Could not find the required columns. Need a date, a description and an amount "
            "(or debit/credit) column."
        )

    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise StatementError(f"Too many rows ({len(rows)}). The limit is {MAX_ROWS}.")

    result = ParseResult()
    order, ambiguous = _slash_order([(row.get(date_col) or "") for row in rows])
    if ambiguous and any("/" in (row.get(date_col) or "") for row in rows):
        result.warnings.append(
            "Dates like 03/04/2024 are ambiguous; read as month/day. Check the dates look right."
        )

    for index, row in enumerate(rows):
        line = index + 2  # header is line 1
        description = " ".join((row.get(desc_col) or "").split())
        if not any((value or "").strip() for value in row.values()):
            continue
        if SUMMARY_ROW.match(description):
            result.issues.append(ParseIssue(line=line, message="Skipped a summary/balance row."))
            continue
        if not description:
            result.issues.append(ParseIssue(line=line, message="Missing description."))
            continue
        try:
            when = parse_date(row.get(date_col) or "", order)
            amount = _row_amount(row, amount_col, debit_col, credit_col)
        except ValueError as error:
            result.issues.append(ParseIssue(line=line, message=str(error)))
            continue
        if amount == 0:
            result.issues.append(ParseIssue(line=line, message="Zero amount."))
            continue
        if positive_is_charge and amount_col:
            amount = -amount
        result.transactions.append(RawTransaction(line=line, date=when, description=description, amount=amount))

    if not result.transactions and not result.issues:
        raise StatementError("No transactions found in the file.")
    _warn_if_signs_look_wrong(result, positive_is_charge and bool(amount_col))
    return result


def _warn_if_signs_look_wrong(result: ParseResult, flipped: bool) -> None:
    """A statement is mostly purchases. If most rows are money in, the sign setting is probably wrong."""
    total = len(result.transactions)
    inflows = sum(1 for t in result.transactions if t.amount > 0)
    if total >= 5 and inflows / total > 0.7:
        advice = (
            "Untick 'Purchases are shown as positive numbers'."
            if flipped
            else "If your purchases are positive numbers, tick 'Purchases are shown as positive numbers'."
        )
        result.warnings.append(
            f"{inflows} of {total} rows look like money coming in, which is unusual for a statement. {advice}"
        )


def _row_amount(row: dict, amount_col: str | None, debit_col: str | None, credit_col: str | None) -> Decimal:
    if amount_col and (row.get(amount_col) or "").strip():
        return parse_amount(row[amount_col])
    debit = (row.get(debit_col) or "").strip() if debit_col else ""
    credit = (row.get(credit_col) or "").strip() if credit_col else ""
    if debit and credit:
        raise ValueError("Row has both a debit and a credit amount.")
    if debit:
        return -abs(parse_amount(debit))
    if credit:
        return abs(parse_amount(credit))
    raise ValueError("Missing amount.")
