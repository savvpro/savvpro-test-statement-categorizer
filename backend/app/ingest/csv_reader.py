"""CSV statement reader – handles messy real-world bank exports."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from typing import Any

from app.ingest.amounts import infer_sign_convention, parse_amount, parse_debit_credit
from app.ingest.columns import map_headers
from app.ingest.dates import infer_date_order, parse_date


@dataclass
class SkippedRow:
    line_number: int
    reason: str
    raw: str


@dataclass
class ParsedStatement:
    rows: list[dict[str, Any]]  # list of {date, description, amount_cents}
    skipped: list[SkippedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    column_mapping: dict[str, int] = field(default_factory=dict)
    sign_convention: str = "normal"  # "normal" | "inverted"
    date_order: str = "mdy"  # "mdy" | "dmy"


def _find_header_row(lines: list[str], delimiter: str) -> int:
    """Skip preamble/bank-info rows before the data table starts."""
    for i, line in enumerate(lines):
        parts = [p.strip().lower() for p in line.split(delimiter)]
        # A header row must contain at least a date-like and description-like column
        has_date = any("date" in p for p in parts)
        desc_words = ("description", "payee", "name", "details", "memo",
                      "narrative", "particulars")
        has_desc = any(w in p for p in parts for w in desc_words)
        if has_date and has_desc:
            return i
    return 0  # fallback: first line


def parse_csv(
    data: bytes,
    encoding: str,
    delimiter: str,
    *,
    invert_sign: bool | None = None,
    prefer_mdy: bool | None = None,
) -> ParsedStatement:
    """Parse CSV bytes into structured transaction rows."""
    text = data.decode(encoding, errors="replace")
    lines = text.splitlines()
    if not lines:
        raise ValueError("Empty file")

    # Find header
    header_row_idx = _find_header_row(lines, delimiter)
    header_line = lines[header_row_idx]
    data_lines = lines[header_row_idx + 1:]

    # Parse header
    reader_header = csv.reader([header_line], delimiter=delimiter)
    headers = next(reader_header)
    col_map = map_headers(headers)

    if "date" not in col_map:
        raise ValueError("Could not find a date column in the CSV header")
    if "description" not in col_map:
        raise ValueError("Could not find a description column in the CSV header")
    if "amount" not in col_map and not ("debit" in col_map or "credit" in col_map):
        raise ValueError("Could not find an amount column (amount, debit, or credit)")

    # Infer date order from the column
    date_col_idx = col_map["date"]
    sample_dates: list[str] = []
    for line in data_lines[:100]:
        parts = line.split(delimiter)
        if len(parts) > date_col_idx:
            sample_dates.append(parts[date_col_idx].strip().strip('"'))
    prefer_mdy_calc, date_ambiguous = infer_date_order(sample_dates)
    if prefer_mdy is None:
        prefer_mdy = prefer_mdy_calc
    date_order_str = "mdy" if prefer_mdy else "dmy"

    warnings: list[str] = []
    if date_ambiguous:
        warnings.append(
            "Date format is ambiguous, defaulting to MM/DD/YYYY. "
            "Use the toggle if your file uses DD/MM/YYYY."
        )

    # Parse rows
    skipped: list[SkippedRow] = []
    rows: list[dict[str, Any]] = []
    reader = csv.reader(data_lines, delimiter=delimiter)

    for line_offset, row in enumerate(reader):
        line_number = header_row_idx + 2 + line_offset  # 1-indexed
        raw_line = delimiter.join(row)

        # Skip blank rows
        if not any(cell.strip() for cell in row):
            skipped.append(SkippedRow(line_number, "Blank row", raw_line))
            continue

        # Try to extract date
        try:
            date_raw = row[date_col_idx].strip().strip('"')
            if not date_raw:
                raise ValueError("Empty date")
            posted = parse_date(date_raw, prefer_mdy=prefer_mdy)
        except (ValueError, IndexError) as e:
            skipped.append(SkippedRow(line_number, f"Cannot parse date: {e}", raw_line))
            continue

        # Description
        try:
            desc = row[col_map["description"]].strip().strip('"')
            if not desc:
                raise ValueError("Empty description")
        except (ValueError, IndexError) as e:
            skipped.append(SkippedRow(line_number, f"Missing description: {e}", raw_line))
            continue

        # Amount
        try:
            if "amount" in col_map:
                raw_amt = row[col_map["amount"]].strip().strip('"')
                amount_cents = parse_amount(raw_amt)
            else:
                debit_str = row[col_map["debit"]].strip().strip('"') if "debit" in col_map else ""
                credit_str = row[col_map["credit"]].strip().strip('"') if "credit" in col_map else ""
                amount_cents = parse_debit_credit(debit_str, credit_str)
        except (ValueError, IndexError) as e:
            skipped.append(SkippedRow(line_number, f"Cannot parse amount: {e}", raw_line))
            continue

        # Skip total/balance rows (common in bank exports)
        if desc.lower() in {"opening balance", "closing balance", "total",
                             "balance carried forward", "balance b/f"}:
            skipped.append(SkippedRow(line_number, f"Skipped summary row: {desc!r}", raw_line))
            continue

        rows.append({
            "line_number": line_number,
            "posted_date": posted,
            "description_raw": desc,
            "amount_cents": amount_cents,
        })

    # Detect sign inversion (credit card exports)
    if invert_sign is None and rows:
        convention = infer_sign_convention([r["amount_cents"] for r in rows])
        if convention == "inverted":
            warnings.append(
                "Detected inverted sign convention (purchases appear positive). "
                "Signs have been flipped automatically, use the toggle to override."
            )
            for r in rows:
                r["amount_cents"] = -r["amount_cents"]
    elif invert_sign is True:
        for r in rows:
            r["amount_cents"] = -r["amount_cents"]

    return ParsedStatement(
        rows=rows,
        skipped=skipped,
        warnings=warnings,
        column_mapping=col_map,
        date_order=date_order_str,
    )
