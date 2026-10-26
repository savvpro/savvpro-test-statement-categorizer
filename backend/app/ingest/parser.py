import csv
import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from app.core.money import MoneyError, to_minor
from app.ingest.amounts import AmountError, parse_amount
from app.ingest.formats import FormatProfile, IngestError, detect_profile
from app.ingest.models import ParsedRow, ParseError, ParseResult

_LINE_BREAK = re.compile(r"\r\n|\n|\r")


class _RowError(Exception):
    pass


def parse(file_bytes: bytes) -> ParseResult:
    """Parse a CSV statement. Every physical line after the header ends up in
    exactly one of rows, errors or skipped. Quoted fields cannot span lines."""
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestError("File is not valid UTF-8 text") from exc

    lines = _LINE_BREAK.split(text)
    if lines and lines[-1] == "":
        lines.pop()  # the newline that ends the last line, not a blank line
    if not lines:
        raise IngestError("File is empty")

    try:
        header = _split(lines[0])
    except _RowError as exc:
        raise IngestError(f"Unreadable header row: {exc}") from exc
    profile = detect_profile(header)
    index = {name.strip(): i for i, name in enumerate(header)}

    rows: list[ParsedRow] = []
    errors: list[ParseError] = []
    skipped: list[int] = []

    for row_number, line in enumerate(lines[1:], start=1):
        if not line.strip():
            skipped.append(row_number)
            continue
        try:
            rows.append(_parse_line(profile, index, row_number, line))
        except _RowError as exc:
            errors.append(ParseError(row_number=row_number, raw_line=line, reason=str(exc)))

    return ParseResult(profile_name=profile.name, rows=rows, errors=errors, skipped=skipped)


def _split(line: str) -> list[str]:
    try:
        return next(csv.reader([line], strict=True), [])
    except csv.Error as exc:
        raise _RowError(f"malformed CSV line: {exc}") from exc


def _parse_line(
    profile: FormatProfile, index: dict[str, int], row_number: int, line: str
) -> ParsedRow:
    cells = _split(line)
    if len(cells) != len(profile.headers):
        raise _RowError(f"expected {len(profile.headers)} columns, got {len(cells)}")

    def cell(column: str) -> str:
        return cells[index[column]]

    description = cell(profile.description_column)
    if not description.strip():
        raise _RowError("description is empty")

    return ParsedRow(
        row_number=row_number,
        date=_parse_date(cell(profile.date_column), profile.date_format),
        raw_description=description,
        amount=_row_amount(profile, cell),
        currency=_row_currency(profile, cell),
        account_type=profile.account_type,
    )


def _parse_date(text: str, date_format: str) -> date:
    value = text.strip()
    try:
        parsed = datetime.strptime(value, date_format)
    except ValueError:
        raise _RowError(f"invalid date {value!r}, expected format {date_format}") from None
    if parsed.strftime(date_format) != value:  # rejects e.g. "2026-9-5"
        raise _RowError(f"invalid date {value!r}, expected format {date_format}")
    return parsed.date()


Cell = Callable[[str], str]


def _row_amount(profile: FormatProfile, cell: Cell) -> Decimal:
    try:
        if profile.amount_mode == "signed":
            amount = parse_amount(cell(profile.amount_column))
        else:
            amount = _debit_credit_amount(cell(profile.debit_column), cell(profile.credit_column))
        to_minor(amount)  # money is stored in minor units: refuse what cannot be stored exactly
    except (AmountError, MoneyError) as exc:
        raise _RowError(str(exc)) from None
    return amount


def _debit_credit_amount(debit_text: str, credit_text: str) -> Decimal:
    has_debit, has_credit = bool(debit_text.strip()), bool(credit_text.strip())
    if has_debit == has_credit:
        found = "both" if has_debit else "neither"
        raise _RowError(f"expected exactly one of debit or credit, got {found}")
    if has_debit:
        debit = parse_amount(debit_text)
        if debit < 0:
            raise _RowError("debit must not be negative")
        return -debit
    credit = parse_amount(credit_text)
    if credit < 0:
        raise _RowError("credit must not be negative")
    return credit


def _row_currency(profile: FormatProfile, cell: Cell) -> str:
    if profile.currency is not None:
        return profile.currency
    currency = cell(profile.currency_column).strip().upper()
    if not currency:
        raise _RowError("currency is empty")
    return currency
