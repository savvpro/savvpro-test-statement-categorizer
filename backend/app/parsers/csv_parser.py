"""
CSV parser – handles the wild variety of bank/credit-card CSV formats.

Features:
 - chardet encoding detection
 - Synonym-based header auto-detection
 - Multiple date format inference (tries all common formats, resolves ambiguity)
 - Single amount column or separate debit/credit columns
 - Column-mapping error with available columns on failure
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import IO

import chardet

from app.brain.normalize import parse_amount_cents
from app.parsers.base import BaseParser, ParseError, RawRow

# ── Header synonyms ────────────────────────────────────────────────────────

_DATE_SYNONYMS = {
    "date", "posted", "posted date", "posting date", "trans date",
    "transaction date", "post date", "settle date", "settlement date",
    "trade date", "effective date",
}

_DESC_SYNONYMS = {
    "description", "memo", "details", "payee", "name", "merchant",
    "transaction description", "trans description", "narrative",
    "reference", "particulars",
}

_AMOUNT_SYNONYMS = {
    "amount", "total", "transaction amount", "trans amount",
    "charge", "value",
}

_DEBIT_SYNONYMS = {
    "debit", "debits", "withdrawals", "withdrawal", "money out",
    "debit amount", "dr",
}

_CREDIT_SYNONYMS = {
    "credit", "credits", "deposits", "deposit", "money in",
    "credit amount", "cr",
}

# ── Date formats to try ─────────────────────────────────────────────────────

_DATE_FORMATS = [
    "%m/%d/%Y",    # 01/15/2026
    "%m/%d/%y",    # 01/15/26
    "%m-%d-%Y",
    "%m-%d-%y",
    "%Y-%m-%d",    # ISO 2026-01-15
    "%Y/%m/%d",
    "%d/%m/%Y",    # DD/MM/YYYY (UK)
    "%d-%m-%Y",
    "%d/%m/%y",
    "%b %d, %Y",   # Jan 15, 2026
    "%B %d, %Y",   # January 15, 2026
    "%d %b %Y",    # 15 Jan 2026
    "%d %B %Y",
    "%m.%d.%Y",
    "%d.%m.%Y",
]


class CsvParser(BaseParser):
    """Parse bank/credit-card CSV statements."""

    def can_handle(self, filename: str, content_type: str | None = None) -> bool:
        return filename.lower().endswith(".csv") or content_type == "text/csv"

    def parse(
        self,
        file: IO[bytes],
        account_type: str = "credit_card",
        *,
        column_mapping: dict[str, str] | None = None,
    ) -> list[RawRow]:
        raw_bytes = file.read()

        # Detect encoding
        detected = chardet.detect(raw_bytes)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        text = raw_bytes.decode(encoding, errors="replace")

        # Strip BOM
        if text.startswith("\ufeff"):
            text = text[1:]

        reader = csv.reader(io.StringIO(text))
        all_rows = list(reader)

        if not all_rows:
            raise ParseError("CSV file is empty")

        # Find header row (first row with enough non-empty cells)
        header_idx = 0
        for i, row in enumerate(all_rows):
            non_empty = sum(1 for c in row if c.strip())
            if non_empty >= 3:
                header_idx = i
                break

        headers = [h.strip().lower() for h in all_rows[header_idx]]
        data_rows = all_rows[header_idx + 1 :]

        # ── Map columns ──────────────────────────────────────────────────
        if column_mapping:
            date_col = _find_col_idx(headers, column_mapping.get("date_col", ""))
            desc_col = _find_col_idx(headers, column_mapping.get("description_col", ""))
            amt_col = _find_col_idx(headers, column_mapping.get("amount_col")) if column_mapping.get("amount_col") else None
            debit_col = _find_col_idx(headers, column_mapping.get("debit_col")) if column_mapping.get("debit_col") else None
            credit_col = _find_col_idx(headers, column_mapping.get("credit_col")) if column_mapping.get("credit_col") else None
        else:
            date_col = _match_header(headers, _DATE_SYNONYMS)
            desc_col = _match_header(headers, _DESC_SYNONYMS, exclude={date_col} if date_col is not None else None)
            amt_col = _match_header(headers, _AMOUNT_SYNONYMS, exclude={c for c in (date_col, desc_col) if c is not None})
            debit_col = _match_header(headers, _DEBIT_SYNONYMS, exclude={c for c in (date_col, desc_col, amt_col) if c is not None})
            credit_col = _match_header(headers, _CREDIT_SYNONYMS, exclude={c for c in (date_col, desc_col, amt_col, debit_col) if c is not None})

        if date_col is None or desc_col is None:
            raise ParseError(
                "Could not auto-detect date and description columns. "
                "Please provide a column mapping.",
                available_columns=[all_rows[header_idx][i] for i in range(len(headers))],
            )

        if amt_col is None and debit_col is None:
            raise ParseError(
                "Could not auto-detect amount column(s). "
                "Please provide a column mapping.",
                available_columns=[all_rows[header_idx][i] for i in range(len(headers))],
            )

        has_separate_cols = (
            debit_col is not None
            and credit_col is not None
            and debit_col != credit_col
            and (amt_col is None or (debit_col != amt_col and credit_col != amt_col))
        )

        # ── Detect date format ───────────────────────────────────────────
        date_values = [
            row[date_col].strip()
            for row in data_rows
            if len(row) > date_col and row[date_col].strip()
        ]
        date_format = _detect_date_format(date_values)
        if date_format is None:
            raise ParseError(
                f"Could not determine date format. Sample values: {date_values[:5]}"
            )

        # ── Parse data rows ──────────────────────────────────────────────
        results: list[RawRow] = []

        for row_idx, row in enumerate(data_rows):
            if len(row) <= max(c for c in [date_col, desc_col, amt_col or 0, debit_col or 0, credit_col or 0] if c is not None):
                continue  # skip short rows

            date_str = row[date_col].strip()
            if not date_str:
                continue

            try:
                posted = datetime.strptime(date_str, date_format).date()
            except ValueError:
                continue  # skip unparseable dates

            description = row[desc_col].strip()
            if not description:
                continue

            # Parse amount
            if has_separate_cols:
                debit_val = row[debit_col].strip() if debit_col is not None and len(row) > debit_col else None
                credit_val = row[credit_col].strip() if credit_col is not None and len(row) > credit_col else None
                amount_cents = parse_amount_cents(
                    None,
                    debit_value=debit_val if debit_val else None,
                    credit_value=credit_val if credit_val else None,
                    account_type=account_type,
                )
            elif amt_col is not None:
                amt_str = row[amt_col].strip()
                amount_cents = parse_amount_cents(amt_str, account_type=account_type)
            else:
                continue

            if amount_cents == 0:
                continue  # skip zero-amount rows

            results.append(RawRow(
                row_index=row_idx,
                posted_date=posted,
                raw_description=description,
                amount_cents=amount_cents,
            ))

        if not results:
            raise ParseError("No valid transaction rows found in the CSV file")

        return results


def _match_header(headers: list[str], synonyms: set[str], exclude: set[int] | None = None) -> int | None:
    """Find the column index matching any synonym."""
    exclude = exclude or set()
    # 1. Exact match
    for i, h in enumerate(headers):
        if i in exclude:
            continue
        if h in synonyms:
            return i
    # 2. Word boundary match
    for i, h in enumerate(headers):
        if i in exclude:
            continue
        for syn in synonyms:
            if re.search(r"\b" + re.escape(syn) + r"\b", h):
                return i
    return None


def _find_col_idx(headers: list[str], col_name: str | None) -> int | None:
    """Find column index by exact or case-insensitive name."""
    if not col_name:
        return None
    target = col_name.strip().lower()
    for i, h in enumerate(headers):
        if h == target:
            return i
    return None


def _detect_date_format(samples: list[str]) -> str | None:
    """
    Try each format on the sample values.
    If a format parses ALL samples, return it.
    If ambiguous (e.g., MM/DD vs DD/MM), prefer the one where no day > 12
    causes a failure.
    """
    if not samples:
        return None

    test_samples = samples[:50]  # test on up to 50 values

    valid_formats: list[str] = []

    for fmt in _DATE_FORMATS:
        ok = True
        for s in test_samples:
            try:
                datetime.strptime(s.strip(), fmt)
            except ValueError:
                ok = False
                break
        if ok:
            valid_formats.append(fmt)

    if not valid_formats:
        return None

    if len(valid_formats) == 1:
        return valid_formats[0]

    # Disambiguate: if we have both MM/DD and DD/MM, check for any value > 12
    # in the first position (which would only work for one format)
    for fmt in valid_formats:
        # Prefer ISO format if available
        if fmt.startswith("%Y"):
            return fmt
        # Prefer US format (MM/DD) as the most common for US bank statements
        if fmt in ("%m/%d/%Y", "%m/%d/%y"):
            return fmt

    return valid_formats[0]
