"""
parser.py

Handles reading the uploaded statement files. Real bank CSVs are messy -
different column names, date formats, amount formats (with $, commas, parens).
This tries to handle all of that gracefully.

Supports CSV and OFX/QFX. Could add PDF parsing later but that's a whole
other level of complexity with table extraction.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Transaction:
    id: str                          # row index as string, e.g. "0"
    date: Optional[str]              # ISO-8601 string or raw value
    description: str
    amount: Optional[float]          # negative = debit, positive = credit
    raw: dict = field(default_factory=dict)   # original row for debugging


# ---------------------------------------------------------------------------
# CSV column name normalisation
# ---------------------------------------------------------------------------

# Different banks use wildly different column names for the same thing.
# Built this list by testing against Chase, Amex, and a couple others.
_DATE_ALIASES = {
    "date", "transaction date", "trans date", "posted date",
    "posting date", "value date", "txn date",
}
_DESC_ALIASES = {
    "description", "merchant", "payee", "name", "memo",
    "transaction description", "details", "narrative",
    "original description", "transaction", "trans description",
}
_AMOUNT_ALIASES = {
    "amount", "transaction amount", "debit", "credit",
    "payment", "charge", "amt", "value",
}


def _find_col(headers: list[str], aliases: set[str]) -> Optional[str]:
    for h in headers:
        if h.strip().lower() in aliases:
            return h
    return None


def _parse_amount(raw: str) -> Optional[float]:
    """Parse amount strings. Banks love to be creative: $1,234.56 or (22.00) for negatives."""
    raw = raw.strip()
    if not raw:
        return None
    # parentheses = negative (common in accounting-style exports)
    negative = raw.startswith("(") and raw.endswith(")")
    raw = re.sub(r"[()$,€£\s]", "", raw)
    try:
        val = float(raw)
        return -val if negative else val
    except ValueError:
        return None


def _normalise_date(raw: str) -> str:
    """Try to return ISO-8601. If parsing fails, return the raw string."""
    raw = raw.strip()
    # Already ISO
    if re.match(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    # MM/DD/YYYY or MM-DD-YYYY
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
    if m:
        month, day, year = m.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    # DD/MM/YYYY (European)
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2})", raw)
    if m:
        part1, part2, year_short = m.groups()
        year = f"20{year_short}" if int(year_short) < 50 else f"19{year_short}"
        return f"{year}-{part1.zfill(2)}-{part2.zfill(2)}"
    return raw


# ---------------------------------------------------------------------------
# CSV parser
# ---------------------------------------------------------------------------

def parse_csv(content: bytes) -> list[Transaction]:
    """Parse a CSV statement and return normalised transactions."""
    text = content.decode("utf-8-sig", errors="replace")  # strip BOM
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("CSV has no header row")

    headers = list(reader.fieldnames)
    date_col = _find_col(headers, _DATE_ALIASES)
    desc_col = _find_col(headers, _DESC_ALIASES)
    amt_col = _find_col(headers, _AMOUNT_ALIASES)

    if not desc_col:
        raise ValueError(
            "Could not find a description / merchant column. "
            f"Headers found: {headers}"
        )

    transactions: list[Transaction] = []
    for idx, row in enumerate(reader):
        raw_desc = row.get(desc_col, "").strip()
        if not raw_desc:
            continue  # skip blank rows

        raw_date = row.get(date_col, "") if date_col else ""
        raw_amt = row.get(amt_col, "") if amt_col else ""

        transactions.append(
            Transaction(
                id=str(idx),
                date=_normalise_date(raw_date) if raw_date else None,
                description=raw_desc,
                amount=_parse_amount(raw_amt) if raw_amt else None,
                raw=dict(row),
            )
        )

    return transactions


# ---------------------------------------------------------------------------
# OFX / QFX parser (text-based, no XML library needed for basic OFX)
# ---------------------------------------------------------------------------

def parse_ofx(content: bytes) -> list[Transaction]:
    """Parse an OFX/QFX file and return normalised transactions."""
    text = content.decode("latin-1", errors="replace")

    # Locate STMTTRN blocks
    blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", text, re.DOTALL | re.IGNORECASE)
    if not blocks:
        # Flat OFX (SGML, no closing tags)
        blocks = re.findall(r"<STMTTRN>(.*?)(?=<STMTTRN>|</BANKTRANLIST>|$)", text, re.DOTALL | re.IGNORECASE)

    transactions: list[Transaction] = []
    for idx, block in enumerate(blocks):

        def _tag(name: str) -> str:
            m = re.search(rf"<{name}>\s*([^\r\n<]+)", block, re.IGNORECASE)
            return m.group(1).strip() if m else ""

        dtposted = _tag("DTPOSTED") or _tag("DTUSER") or ""
        # OFX dates: YYYYMMDD[HHMMSS[.xxx][timezone]]
        if dtposted and re.match(r"\d{8}", dtposted):
            dtposted = f"{dtposted[:4]}-{dtposted[4:6]}-{dtposted[6:8]}"

        raw_amt = _tag("TRNAMT")
        description = _tag("MEMO") or _tag("NAME") or _tag("PAYEE") or ""

        transactions.append(
            Transaction(
                id=str(idx),
                date=dtposted or None,
                description=description,
                amount=_parse_amount(raw_amt) if raw_amt else None,
            )
        )

    return transactions


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_statement(filename: str, content: bytes) -> list[Transaction]:
    """
    Detect format by filename extension and return parsed transactions.

    Raises:
        ValueError: if the format is not supported or parsing fails.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "csv":
        return parse_csv(content)
    elif ext in {"ofx", "qfx"}:
        return parse_ofx(content)
    else:
        # Try CSV as fallback
        try:
            return parse_csv(content)
        except Exception:
            raise ValueError(
                f"Unsupported file type '.{ext}'. Please upload a CSV or OFX/QFX file."
            )
