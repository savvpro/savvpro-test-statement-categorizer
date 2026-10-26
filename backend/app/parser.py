"""Reads a bank or credit-card CSV into clean rows.

Real exports are messy: different column names, a few lines of account info above the
header, semicolon delimiters, "1,234.50" and "(500.00)" amounts, Excel's BOM, dd/mm dates.
The parser never crashes on one bad row. It skips the row and says why, with the row number.
"""

import codecs
import csv
import io
import itertools
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from dateutil import parser as dateparser

from .models import RowIssue, Transaction

MAX_HEADER_SCAN = 30  # how many lines to look through for the header row
MAX_DESCRIPTION_LENGTH = 300
MAX_AMOUNT = Decimal("1e12")

# Header names we recognise, most preferred first. Compared lower-case with any
# "(PKR)"-style suffix removed.
ALIASES: dict[str, tuple[str, ...]] = {
    "date": (
        "date",
        "transaction date",
        "txn date",
        "posting date",
        "posted date",
        "booking date",
        "value date",
    ),
    "description": (
        "description",
        "details",
        "narration",
        "particulars",
        "transaction details",
        "merchant",
        "payee",
        "memo",
    ),
    "amount": ("amount", "transaction amount"),
    "debit": ("debit", "debit amount", "withdrawal", "withdrawals", "money out", "paid out", "dr"),
    "credit": ("credit", "credit amount", "deposit", "deposits", "money in", "paid in", "cr"),
}

_CURRENCY = re.compile(r"\b(?:PKR|RS|USD|EUR|GBP|AED)\b\.?|[₨$£€]", re.IGNORECASE)
_ISO_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ].*)?$")
_SUMMARY_LINE = re.compile(
    r"^(?:(?:OPENING|CLOSING|BEGINNING|ENDING|STARTING)\s+BALANCE|BROUGHT FORWARD|CARRIED FORWARD"
    r"|BALANCE\s+(?:B/?F|C/?F)|TOTALS?|SUB\s?TOTAL|GRAND TOTAL|BALANCE)\s*:?$",
    re.IGNORECASE,
)
# Two different defaults reveal dates with a missing part ("10/2026") that dateutil
# would otherwise silently fill in from today's date.
_DEFAULT_A = datetime(2000, 1, 1)
_DEFAULT_B = datetime(2001, 2, 2)


class StatementParseError(ValueError):
    """The file as a whole cannot be used (empty, not a CSV, no usable columns)."""


class RowError(ValueError):
    """One row cannot be used. The row is skipped and the reason is reported."""


@dataclass
class ParseResult:
    transactions: list[Transaction] = field(default_factory=list)
    skipped: list[RowIssue] = field(default_factory=list)
    warnings: list[RowIssue] = field(default_factory=list)


# ---------------------------------------------------------------- values


def parse_amount(raw: str | None) -> Decimal | None:
    """'1,234.50' -> 1234.50, '(500.00)' -> -500.00, 'Rs 1,200' -> 1200, '' -> None.

    Raises ValueError for anything that is not clearly a money amount (including
    NaN/Infinity and numbers with more than two decimals, which we refuse to round).
    """
    if raw is None or not raw.strip():
        return None
    text = _CURRENCY.sub("", raw).strip()

    negative = False
    if suffix := re.search(r"\s*(CR|DR)$", text, re.IGNORECASE):
        negative = suffix.group(1).upper() == "DR"
        text = text[: suffix.start()].strip()
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1].strip()
    if text.startswith("-"):
        negative, text = True, text[1:].strip()
    elif text.endswith("-"):
        negative, text = True, text[:-1].strip()
    elif text.startswith("+"):
        text = text[1:].strip()

    text = text.replace(" ", "").replace("'", "")
    if "," in text and "." in text:
        # The right-most separator is the decimal one: 1,234.50 or 1.234,50
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", text):  # 1,234 or 12,345,678
            text = text.replace(",", "")
        elif re.fullmatch(r"\d+,\d{1,2}", text):  # 12,50
            text = text.replace(",", ".")

    # fullmatch (not float()) so "nan", "inf" and "1e5" are rejected
    if not re.fullmatch(r"\d+(\.\d+)?|\.\d+", text):
        raise ValueError(f"'{raw.strip()}' is not a valid amount")
    if "." in text and len(text.split(".")[1]) > 2:
        raise ValueError(f"'{raw.strip()}' has more than 2 decimal places")
    value = Decimal(text)
    if value >= MAX_AMOUNT:
        raise ValueError(f"'{raw.strip()}' is too large to be a real amount")
    return -value if negative else value


def parse_date(raw: str | None) -> date:
    """Day-first by default (01/10/2026 is 1 October). ISO dates are read as ISO."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("missing date")
    if iso := _ISO_DATE.match(text):
        try:
            return date(int(iso[1]), int(iso[2]), int(iso[3]))
        except ValueError:
            raise ValueError(f"'{text}' is not a real calendar date") from None
    try:
        first = dateparser.parse(text, dayfirst=True, default=_DEFAULT_A)
        second = dateparser.parse(text, dayfirst=True, default=_DEFAULT_B)
    except (ValueError, OverflowError):
        raise ValueError(f"'{text}' is not a valid date") from None
    if first != second:
        raise ValueError(f"'{text}' is an incomplete date")
    return first.date()


# ---------------------------------------------------------------- file


def _decode(content: bytes) -> str:
    if content.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return content.decode("utf-16")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("latin-1")  # never fails


def _detect_delimiter(text: str) -> str:
    """Pick the delimiter that splits the first lines into the most consistent width."""
    sample = text[:20_000]
    best, best_width = ",", 0
    for delimiter in (",", ";", "\t", "|"):
        try:
            rows = list(itertools.islice(csv.reader(io.StringIO(sample), delimiter=delimiter), 30))
        except csv.Error:
            continue
        widths = [len(r) for r in rows if r]
        if not widths:
            continue
        width, count = Counter(widths).most_common(1)[0]
        if count >= max(2, len(widths) // 2) and width > best_width:
            best, best_width = delimiter, width
    return best


def _normalise_header(cell: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", cell)).strip().lower()


def _map_columns(cells: list[str]) -> dict[str, int] | None:
    """Column positions if this row is a usable header, else None."""
    headers = [_normalise_header(c) for c in cells]
    columns: dict[str, int] = {}
    for key, aliases in ALIASES.items():
        for alias in aliases:
            if alias in headers:
                columns[key] = headers.index(alias)
                break
    has_money = "amount" in columns or "debit" in columns or "credit" in columns
    if "date" in columns and "description" in columns and has_money:
        return columns
    return None


def _cell(cells: list[str], index: int | None) -> str:
    return cells[index] if index is not None and index < len(cells) else ""


def _parse_row(
    line: int, cells: list[str], columns: dict[str, int], purchases_positive: bool
) -> Transaction:
    description = re.sub(r"\s+", " ", _cell(cells, columns["description"])).strip()
    if not description:
        raise RowError("missing description")
    if _SUMMARY_LINE.match(description):
        raise RowError("balance/total line, not a transaction")
    description = description[:MAX_DESCRIPTION_LENGTH]

    try:
        when = parse_date(_cell(cells, columns["date"]))
    except ValueError as exc:
        raise RowError(str(exc)) from None

    try:
        if "debit" in columns or "credit" in columns:
            debit = parse_amount(_cell(cells, columns.get("debit")))
            credit = parse_amount(_cell(cells, columns.get("credit")))
            if debit is None and credit is None:
                raise RowError("no debit or credit amount")
            if debit and credit:
                raise RowError("both Debit and Credit are filled in")
            # abs(): some banks print debits as negatives, some as positives
            amount = abs(credit or Decimal(0)) - abs(debit or Decimal(0))
        else:
            single = parse_amount(_cell(cells, columns["amount"]))
            if single is None:
                raise RowError("missing amount")
            amount = -single if purchases_positive else single
    except ValueError as exc:
        if isinstance(exc, RowError):
            raise
        raise RowError(str(exc)) from None

    if amount == 0:
        raise RowError("amount is zero")
    return Transaction(row=line, date=when, description=description, amount=amount)


def parse_statement(
    content: bytes, *, purchases_positive: bool = False, max_rows: int = 5000
) -> ParseResult:
    """Parse a statement CSV.

    `purchases_positive` is for credit-card exports with a single Amount column where
    spending is positive (the opposite of a bank account).
    """
    if not content.strip():
        raise StatementParseError("The file is empty.")
    is_utf16 = content.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
    if content.startswith(b"PK") or (b"\x00" in content[:4096] and not is_utf16):
        raise StatementParseError(
            "This looks like a binary file (for example an Excel workbook). "
            "Export the statement as CSV and upload that."
        )

    text = _decode(content)
    delimiter = _detect_delimiter(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        lines = [(reader.line_num, row) for row in reader]
    except csv.Error as exc:
        raise StatementParseError(f"This does not look like a valid CSV file ({exc}).") from None

    header_at, columns = None, None
    for index, (_, cells) in enumerate(lines[:MAX_HEADER_SCAN]):
        if columns := _map_columns(cells):
            header_at = index
            break
    if columns is None or header_at is None:
        first = next((cells for _, cells in lines if any(c.strip() for c in cells)), [])
        raise StatementParseError(
            "Could not find the columns. Expected a Date column, a Description column and "
            "either an Amount column or Debit/Credit columns. "
            f"The first row has: {', '.join(c.strip() for c in first if c.strip()) or 'nothing'}."
        )

    result = ParseResult()
    seen = 0
    for line, cells in lines[header_at + 1 :]:
        if not any(c.strip() for c in cells):
            continue
        seen += 1
        if seen > max_rows:
            raise StatementParseError(f"This statement has more than {max_rows} rows.")
        try:
            result.transactions.append(_parse_row(line, cells, columns, purchases_positive))
        except RowError as exc:
            result.skipped.append(RowIssue(row=line, message=str(exc)))

    if not result.transactions:
        raise StatementParseError("No usable transactions were found in this file.")

    groups: dict[tuple, list[int]] = defaultdict(list)
    for t in result.transactions:
        groups[(t.date, t.description.casefold(), t.amount)].append(t.row)
    for rows in groups.values():
        if len(rows) > 1:
            where = ", ".join(str(r) for r in rows)
            result.warnings.append(
                RowIssue(
                    row=rows[0],
                    message=(
                        f"Rows {where} look identical. All were kept; check for a double charge."
                    ),
                )
            )
    return result
