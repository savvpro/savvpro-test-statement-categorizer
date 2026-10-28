"""CSV reader: delimiter sniffing, header detection, column mapping, row validation."""

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from app.core.errors import ParseError
from app.domain.models import ParseResult, ParseWarning, RawTransaction
from app.ingest import amounts, dates
from app.ingest.common import RowError, enforce_failure_policy

DELIMITERS = ",;\t|"
HEADER_SCAN_ROWS = 25
MAX_COLUMNS = 64

SYNONYMS: dict[str, tuple[str, ...]] = {
    "date": (
        "date",
        "posted date",
        "posting date",
        "transaction date",
        "trans date",
        "post date",
        "value date",
    ),
    "description": (
        "description",
        "payee",
        "merchant",
        "name",
        "details",
        "transaction description",
        "narrative",
    ),
    "memo": ("memo", "notes", "reference", "additional info"),
    "amount": ("amount", "transaction amount", "amount (usd)", "value"),
    "debit": ("debit", "withdrawal", "withdrawals", "money out", "paid out", "charges"),
    "credit": ("credit", "deposit", "deposits", "money in", "paid in", "payments"),
    "type": ("type", "transaction type", "dr/cr", "debit/credit"),
    "status": ("status",),
}
_POSTED_DATES = ("posteddate", "postingdate", "postdate")
_SUMMARY_RE = re.compile(
    r"^\s*(TOTAL|ENDING BALANCE|BEGINNING BALANCE|OPENING BALANCE|CLOSING BALANCE)",
    re.IGNORECASE,
)


def _norm(cell: str) -> str:
    return re.sub(r"[^a-z0-9]", "", cell.lower())


_LOOKUP: dict[str, str] = {_norm(s): f for f, syns in SYNONYMS.items() for s in syns}


@dataclass
class _Columns:
    index: dict[str, int] = field(default_factory=dict)

    def get(self, row: list[str], name: str) -> str | None:
        i = self.index.get(name)
        if i is None or i >= len(row):
            return None
        value = row[i].strip()
        return value or None


def _count_outside_quotes(line: str, delim: str) -> int:
    count = 0
    quoted = False
    for ch in line:
        if ch == '"':
            quoted = not quoted
        elif ch == delim and not quoted:
            count += 1
    return count


def sniff_delimiter(text: str) -> str:
    """Most consistent delimiter over the first 10 non-empty lines; csv.Sniffer as a fallback."""
    lines = [ln for ln in text.split("\n", 400) if ln.strip()][:10]
    best: tuple[int, int, int] = (0, 0, 0)
    best_delim = ""
    for rank, d in enumerate(DELIMITERS):
        counts = [_count_outside_quotes(ln, d) for ln in lines]
        positive = [c for c in counts if c > 0]
        if not positive:
            continue
        mode, freq = Counter(positive).most_common(1)[0]
        score = (freq, mode, -rank)
        if score > best:
            best, best_delim = score, d
    if best_delim:
        return best_delim
    try:
        return csv.Sniffer().sniff(text[:4096], delimiters=DELIMITERS).delimiter
    except csv.Error:
        return ","


def _find_header(rows: list[list[str]]) -> tuple[int, dict[str, int]]:
    for i, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        mapping: dict[str, int] = {}
        matched = 0
        for j, cell in enumerate(row):
            key = _norm(cell)
            fld = _LOOKUP.get(key)
            if fld is None:
                continue
            matched += 1
            if fld == "date":
                # prefer a "posted" date over a transaction date
                if "date" not in mapping or (
                    key in _POSTED_DATES and _norm(row[mapping["date"]]) not in _POSTED_DATES
                ):
                    mapping["date"] = j
            elif fld not in mapping:
                mapping[fld] = j
        if matched >= 2:
            return i, mapping
    raise ParseError(
        f"No header row found in the first {HEADER_SCAN_ROWS} rows. "
        "Expected columns such as: date, description, amount (or debit/credit)",
        code="NO_HEADER",
    )


def _check_required(mapping: dict[str, int]) -> None:
    missing: list[str] = []
    if "date" not in mapping:
        missing.append("date")
    if "description" not in mapping:
        missing.append("description")
    if "amount" not in mapping and not ({"debit", "credit"} & mapping.keys()):
        missing.append("amount (or debit/credit)")
    if missing:
        raise ParseError(
            "Missing required column(s): " + ", ".join(missing),
            code="MISSING_COLUMNS",
            errors=[{"missing": missing}],
        )


def _read_rows(text: str, delim: str) -> list[list[str]]:
    csv.field_size_limit(1_000_000)
    try:
        return list(csv.reader(io.StringIO(text, newline=""), delimiter=delim))
    except csv.Error as exc:
        raise ParseError(f"Malformed CSV: {exc}", code="MALFORMED_CSV") from exc


@dataclass(frozen=True, slots=True)
class _Ok:
    extra_precision: bool
    future: bool


def _validate_row(
    cols: _Columns, row: list[str], date_raw: str, fmt: str | None, decimal_comma: bool
) -> RowError | _Ok:
    if fmt is None:
        return RowError(0, "BAD_DATE", f"cannot parse date {date_raw!r}")
    try:
        d = dates.parse_date(date_raw, fmt)
    except dates.DateError as exc:
        return RowError(0, exc.code, str(exc))
    values: dict[str, Decimal] = {}
    extra_precision = False
    for key in ("amount", "debit", "credit"):
        raw = cols.get(row, key)
        if raw is None:
            continue
        try:
            values[key] = amounts.parse_amount(raw, decimal_comma=decimal_comma)
        except amounts.AmountError as exc:
            return RowError(0, exc.code, str(exc))
        extra_precision = extra_precision or amounts.has_extra_precision(values[key])
    if not values:
        return RowError(0, "EMPTY_AMOUNT", "no amount on this row")
    if "amount" not in values and values.get("debit") and values.get("credit"):
        return RowError(0, "BOTH_DEBIT_CREDIT", "row has both a debit and a credit amount")
    return _Ok(extra_precision, dates.is_future(d))


def parse_csv(text: str, *, max_rows: int) -> ParseResult:
    delim = sniff_delimiter(text)
    all_rows = _read_rows(text, delim)
    header_idx, mapping = _find_header(all_rows)
    _check_required(mapping)
    headers = all_rows[header_idx]
    if len(headers) > MAX_COLUMNS:
        raise ParseError(f"More than {MAX_COLUMNS} columns", code="TOO_MANY_COLUMNS")
    cols = _Columns(mapping)
    warnings: list[ParseWarning] = []
    if header_idx > 0 and any(any(c.strip() for c in r) for r in all_rows[:header_idx]):
        warnings.append(
            ParseWarning("PREAMBLE_SKIPPED", f"Skipped {header_idx} line(s) before the header row")
        )

    candidates: list[tuple[int, list[str]]] = []
    errors: list[RowError] = []
    needed = max(mapping["date"], mapping["description"])
    for n, row in enumerate(all_rows[header_idx + 1 :], start=1):
        if not any(c.strip() for c in row):
            continue
        desc = cols.get(row, "description") or ""
        date_cell = cols.get(row, "date")
        has_amount = any(cols.get(row, k) for k in ("amount", "debit", "credit"))
        if (
            _SUMMARY_RE.match(desc)
            or _SUMMARY_RE.match(date_cell or "")
            or (date_cell is None and has_amount and len(row) > needed)
        ):
            warnings.append(ParseWarning("SUMMARY_ROW_SKIPPED", "Summary/footer row skipped", n))
            continue
        if len(row) <= needed or date_cell is None or not has_amount:
            errors.append(RowError(n, "MALFORMED_ROW", "Row is missing required cells"))
            continue
        candidates.append((n, row))
        if len(candidates) > max_rows:
            raise ParseError(f"More than {max_rows} rows", code="ROW_LIMIT")

    inference = dates.infer_format([cols.get(r, "date") or "" for _, r in candidates])
    fmt = inference.fmt
    if inference.ambiguous:
        warnings.append(
            ParseWarning(
                "AMBIGUOUS_DATE_ORDER",
                "All dates fit both month/day and day/month; assuming month/day (US)",
            )
        )
    money_cols = [k for k in ("amount", "debit", "credit") if k in mapping]
    money_values = [v for _, r in candidates for k in money_cols if (v := cols.get(r, k))]
    decimal_comma = amounts.detect_decimal_comma(money_values)
    if decimal_comma:
        warnings.append(ParseWarning("DECIMAL_COMMA", "Amounts use a decimal comma (1.234,56)"))

    mapped = set(mapping.values())
    rows: list[RawTransaction] = []
    extra_precision = False
    future: list[ParseWarning] = []
    for n, row in candidates:
        date_raw = cols.get(row, "date") or ""
        res = _validate_row(cols, row, date_raw, fmt, decimal_comma)
        if isinstance(res, RowError):
            errors.append(RowError(n, res.code, res.message))
            continue
        extra_precision = extra_precision or res.extra_precision
        if res.future:
            future.append(ParseWarning("FUTURE_DATE", "Date is in the future", n))
        extra = {
            headers[i].strip(): row[i].strip()
            for i in range(min(len(headers), len(row)))
            if i not in mapped and headers[i].strip() and row[i].strip()
        }
        rows.append(
            RawTransaction(
                row_index=n,
                date_raw=date_raw,
                description_raw=cols.get(row, "description") or "",
                amount_raw=cols.get(row, "amount"),
                debit_raw=cols.get(row, "debit"),
                credit_raw=cols.get(row, "credit"),
                memo_raw=cols.get(row, "memo"),
                type_raw=cols.get(row, "type"),
                status_raw=cols.get(row, "status"),
                extra=extra,
            )
        )
    enforce_failure_policy(errors, len(rows))
    warnings.extend(
        ParseWarning(e.code, e.message, e.row_index)
        for e in sorted(errors, key=lambda e: e.row_index)
    )
    warnings.extend(future)
    if extra_precision:
        warnings.append(
            ParseWarning("EXTRA_PRECISION", "Some amounts had more than 2 decimals; rounded")
        )
    return ParseResult(
        rows=tuple(rows),
        warnings=tuple(warnings),
        date_format=fmt,
        decimal_comma=decimal_comma,
    )
