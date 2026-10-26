"""
PDF parser – best-effort extraction using pdfplumber.

Attempts table extraction first, then falls back to text line parsing.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import IO

import pdfplumber

from app.brain.normalize import parse_amount_cents
from app.parsers.base import BaseParser, ParseError, RawRow

# Regex for a typical statement line: date description amount
_LINE_PATTERN = re.compile(
    r"^(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\s+"  # date
    r"(.+?)\s+"                                    # description (non-greedy)
    r"(-?\$?[\d,]+\.\d{2})\s*$"                   # amount
)

_DATE_FORMATS_PDF = [
    "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y",
    "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d",
]

# Headers / footers to skip
_SKIP_PATTERNS = [
    re.compile(r"page\s+\d+\s+of\s+\d+", re.I),
    re.compile(r"statement\s+(period|date|closing)", re.I),
    re.compile(r"(opening|closing|previous|new)\s+balance", re.I),
    re.compile(r"account\s+(number|summary)", re.I),
    re.compile(r"continued\s+on\s+next\s+page", re.I),
    re.compile(r"^\s*(date)\s+(description)\s+(amount|debit|credit)", re.I),
]


class PdfParser(BaseParser):
    """Parse bank/credit-card PDF statements."""

    def can_handle(self, filename: str, content_type: str | None = None) -> bool:
        return (
            filename.lower().endswith(".pdf")
            or content_type == "application/pdf"
        )

    def parse(self, file: IO[bytes], account_type: str = "credit_card") -> list[RawRow]:
        try:
            pdf = pdfplumber.open(file)
        except Exception as exc:
            raise ParseError(f"Could not open PDF: {exc}")

        rows: list[RawRow] = []
        row_idx = 0

        for page in pdf.pages:
            # Try table extraction first
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for table_row in table:
                        if not table_row or len(table_row) < 3:
                            continue
                        result = _parse_table_row(table_row, row_idx, account_type)
                        if result:
                            rows.append(result)
                            row_idx += 1
            else:
                # Fall back to text extraction
                text = page.extract_text() or ""
                pending_desc = ""
                pending_date = None

                for line in text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if any(p.search(line) for p in _SKIP_PATTERNS):
                        continue

                    match = _LINE_PATTERN.match(line)
                    if match:
                        # If we have a pending multi-line description, finalize it
                        date_str, desc, amt_str = match.groups()
                        posted = _parse_date(date_str)
                        if posted is None:
                            continue
                        amount_cents = parse_amount_cents(amt_str, account_type=account_type)
                        if amount_cents == 0:
                            continue
                        rows.append(RawRow(
                            row_index=row_idx,
                            posted_date=posted,
                            raw_description=desc.strip(),
                            amount_cents=amount_cents,
                        ))
                        row_idx += 1
                        pending_desc = ""
                        pending_date = None
                    else:
                        # Possible multi-line continuation
                        if pending_date and line and not re.match(r"^\d{1,2}[/\-.]", line):
                            pending_desc += " " + line

        pdf.close()

        if not rows:
            raise ParseError("No transaction rows found in the PDF")

        return rows


def _parse_table_row(
    cells: list[str | None],
    row_idx: int,
    account_type: str,
) -> RawRow | None:
    """Try to extract date, description, amount from a table row."""
    # Filter out None cells
    cleaned = [c.strip() if c else "" for c in cells]
    cleaned = [c for c in cleaned if c]

    if len(cleaned) < 3:
        return None

    # Try first cell as date
    posted = _parse_date(cleaned[0])
    if posted is None:
        return None

    # Last cell(s) as amount
    amount_cents = 0
    desc_end = len(cleaned) - 1
    for i in range(len(cleaned) - 1, 0, -1):
        try:
            amount_cents = parse_amount_cents(cleaned[i], account_type=account_type)
            if amount_cents != 0:
                desc_end = i
                break
        except (ValueError, IndexError):
            continue

    if amount_cents == 0:
        return None

    description = " ".join(cleaned[1:desc_end]).strip()
    if not description:
        return None

    return RawRow(
        row_index=row_idx,
        posted_date=posted,
        raw_description=description,
        amount_cents=amount_cents,
    )


def _parse_date(s: str) -> "date | None":
    """Try multiple date formats."""
    s = s.strip()
    for fmt in _DATE_FORMATS_PDF:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
