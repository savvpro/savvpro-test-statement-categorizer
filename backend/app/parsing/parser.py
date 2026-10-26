import re
from dataclasses import dataclass
from datetime import date

from app.brain.models import AccountType, ParsedRow
from app.parsing import signs
from app.parsing.amounts import parse_amount, parse_amount_with_marker
from app.parsing.columns import ColumnMap, detect_header, normalize_header
from app.parsing.dates import DateOrder, detect_date_order, parse_date
from app.parsing.errors import MAX_ROWS, EmptyFileError, TooManyRowsError
from app.parsing.readers import SourceRow, read_table
from app.parsing.result import DetectedFormat, ParseResult, RowError

# Full-cell matches only, so a merchant like "TOTAL WINE" is never mistaken for a footer.
_BALANCE_RE = re.compile(
    r"^(?:(?:opening|closing|ending|beginning|starting) balance"
    r"|balance (?:brought |carried )?forward)$"
)
_TOTAL_RE = re.compile(r"^totals?\b")
_PENDING_PREFIX_RE = re.compile(r"^PENDING\b[\s:*\-]*", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class _Draft:
    line_no: int
    date: date
    description: str
    amounts: signs.AmountFields
    is_pending: bool
    raw: dict[str, str]


def parse_statement(
    content: bytes,
    filename: str,
    account_type: AccountType,
    charges_positive: bool | None = None,
) -> ParseResult:
    """Parse a CSV or XLSX statement into canonical rows (> 0 money in, < 0 money out)."""
    table = read_table(content, filename)
    columns = detect_header(table.rows)
    data = [row for row in table.rows[columns.position + 1 :] if any(row.cells)]
    if len(data) > MAX_ROWS:
        raise TooManyRowsError(MAX_ROWS)

    warnings: list[str] = []
    errors: list[RowError] = []
    date_order = detect_date_order(columns.cell(row.cells, "date") for row in data)
    type_column = "type" in columns.fields and signs.is_type_column(
        [columns.cell(row.cells, "type") for row in data]
    )

    drafts: list[_Draft] = []
    for row in data:
        raw = columns.raw(row.cells)
        if label := _summary_label(row, columns, date_order):
            warnings.append(f"line {row.line_no}: skipped summary row {label!r}")
            continue
        try:
            drafts.append(_draft(row, columns, date_order, type_column, raw))
        except ValueError as exc:
            errors.append(RowError(row.line_no, str(exc), raw))

    if not drafts and not errors:
        raise EmptyFileError(f"{filename} has a header but no transactions")

    if charges_positive is not None and (
        account_type is not AccountType.credit_card or columns.split_amounts or type_column
    ):
        warnings.append("charges_positive only applies to single-column credit card files; ignored")
        charges_positive = None

    decision = signs.decide(
        [(d.description, d.amounts) for d in drafts],
        account_type=account_type,
        split_amounts=columns.split_amounts,
        type_column=type_column,
        charges_positive=charges_positive,
    )
    if decision.warning:
        warnings.append(decision.warning)

    rows = [
        ParsedRow(
            row_index=index,
            date=draft.date,
            description=draft.description,
            amount=signs.apply(draft.amounts, decision.convention, account_type),
            is_pending=draft.is_pending,
            raw=draft.raw,
        )
        for index, draft in enumerate(drafts)
    ]
    detected = DetectedFormat(
        file_type=table.file_type,
        encoding=table.encoding,
        delimiter=table.delimiter,
        header_line=columns.line_no,
        column_map=columns.describe(),
        date_order=date_order.value,
        sign_convention=decision.convention.value,
        sign_reason=decision.reason,
    )
    return ParseResult(rows=rows, errors=errors, warnings=warnings, detected=detected)


def _summary_label(row: SourceRow, columns: ColumnMap, order: DateOrder) -> str | None:
    """Return the cell that marks a balance/total row, or None for a normal row.

    Balance rows must match a whole cell. TOTAL rows also need a missing or invalid date, so a
    dated purchase at a merchant called "TOTAL ..." is still a transaction.
    """
    for cell in row.cells:
        if _BALANCE_RE.match(normalize_header(cell)):
            return cell
    for cell in row.cells:
        if _TOTAL_RE.match(normalize_header(cell)):
            try:
                parse_date(columns.cell(row.cells, "date"), order)
            except ValueError:
                return cell
            return None
    return None


def _draft(
    row: SourceRow, columns: ColumnMap, order: DateOrder, type_column: bool, raw: dict[str, str]
) -> _Draft:
    txn_date = parse_date(columns.cell(row.cells, "date"), order)

    description = columns.cell(row.cells, "description")
    is_pending = "pending" in columns.cell(row.cells, "status").lower()
    if _PENDING_PREFIX_RE.match(description):
        is_pending = True
        description = _PENDING_PREFIX_RE.sub("", description) or description
    if not description:
        raise ValueError("missing description")

    return _Draft(
        row.line_no, txn_date, description, _amounts(row, columns, type_column), is_pending, raw
    )


def _amounts(row: SourceRow, columns: ColumnMap, type_column: bool) -> signs.AmountFields:
    if columns.split_amounts:
        debit = parse_amount(columns.cell(row.cells, "debit"))
        credit = parse_amount(columns.cell(row.cells, "credit"))
        if debit is None and credit is None:
            raise ValueError("missing amount: both debit and credit are empty")
        return signs.AmountFields(debit=debit, credit=credit)

    amount, marker = parse_amount_with_marker(columns.cell(row.cells, "amount"))
    if amount is None:
        raise ValueError("missing amount")
    if not type_column:
        return signs.AmountFields(amount=amount, marker=marker)

    type_value = signs.normalize_type(columns.cell(row.cells, "type"))
    if type_value not in signs.DEBIT_TYPES | signs.CREDIT_TYPES:
        raise ValueError("missing DR/CR type")
    return signs.AmountFields(amount=amount, type_value=type_value)
