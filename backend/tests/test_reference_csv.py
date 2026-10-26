"""A real UK council purchase-card export, read through the same path as any upload."""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.models import ParsedStatement, SourceFormat
from app.parsing.csv_reader import read_csv

SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "sample-data"
    / "reference"
    / "stockport-purchase-card"
    / "purchase-card-2026-08.csv"
)

pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="reference sample not present")

HEADER = "Organisation Name,Supplier (Beneficiary),Procurement (Merchant) Category,Purchase Date"


@pytest.fixture(scope="module")
def raw_lines() -> list[str]:
    return SAMPLE.read_bytes().decode("utf-8-sig").splitlines()


@pytest.fixture(scope="module")
def data_rows(raw_lines) -> list[list[str]]:
    """Rows under the header that carry any value, read with the csv module directly."""
    header_at = next(i for i, line in enumerate(raw_lines) if line.startswith(HEADER))
    rows = list(csv.reader(raw_lines[header_at + 1 :]))
    return [r for r in rows if any(cell.strip() for cell in r)]


@pytest.fixture(scope="module")
def parsed() -> ParsedStatement:
    return read_csv(SAMPLE.read_bytes(), max_rows=5000)


def test_file_starts_with_a_bom_title_and_blank_line(raw_lines):
    assert SAMPLE.read_bytes().startswith(b"\xef\xbb\xbf")
    assert raw_lines[0].startswith("AUGUST 2026")
    assert not raw_lines[1].strip(",")
    assert raw_lines[2].startswith(HEADER)


def test_header_is_found_and_the_preamble_skipped(parsed, raw_lines):
    assert parsed.source_format is SourceFormat.CSV
    # Line numbers are file lines: the first purchase sits right under the header on line 4.
    assert parsed.rows[0].line == 4
    assert raw_lines[3].startswith("STOCKPORT MBC,STRAWBURY STAYS")
    assert not any("AUGUST" in r.raw for r in parsed.rejected)


def test_currency_comes_from_the_amount_header(parsed):
    assert parsed.currency_hint == "GBP"


def test_every_data_line_becomes_a_row(parsed, data_rows, raw_lines):
    # 413 lines follow the header in the file; the blank ",,,,," lines at the end are noise.
    assert len(raw_lines) - 3 >= len(data_rows)
    assert len(parsed.rows) == len(data_rows) == 360
    assert not parsed.rejected


def test_purchase_dates_are_day_first_and_not_the_settlement_date(parsed, data_rows):
    expected = [datetime.strptime(r[3], "%d/%m/%Y").date() for r in data_rows]
    assert [r.date for r in parsed.rows] == expected
    assert parsed.rows[0].date.isoformat() == "2026-08-27"
    assert not parsed.warnings  # 27/08/2026 settles the day/month question


def test_amounts_with_quotes_thousands_separators_and_no_leading_zero(parsed, data_rows):
    expected = [Decimal(r[5].replace(",", "")) for r in data_rows]
    assert [r.amount for r in parsed.rows] == expected
    assert parsed.rows[0].amount == Decimal("1400.70")
    assert any(r[5].startswith(".") for r in data_rows)  # printed as ".90", not "0.90"
    assert Decimal("0.90") in expected
    assert any(a < 0 for a in expected)  # refunds stay negative
    assert all(r.debit is None and r.credit is None for r in parsed.rows)


def test_description_is_the_supplier_and_duplicates_are_kept(parsed, data_rows):
    assert [r.description for r in parsed.rows] == [" ".join(r[1].split()) for r in data_rows]
    keys = [(r.date, r.description, r.amount) for r in parsed.rows]
    assert len(keys) > len(set(keys))  # the council really did buy the same thing twice


def test_rejected_rows_always_say_why(parsed):
    for rejected in parsed.rejected:
        assert rejected.reason.strip()
        assert rejected.line > 3


def test_bad_lines_in_the_same_layout_are_rejected_with_reasons(raw_lines):
    header = raw_lines[2]
    bad = [
        "STOCKPORT MBC,SHOP A,GROCERY,31/02/2026,16.09.2026,10.00",  # no such day
        "STOCKPORT MBC,SHOP B,GROCERY,27/08/2026,16.09.2026,n/a",
        "STOCKPORT MBC,,GROCERY,27/08/2026,16.09.2026,10.00",
        "STOCKPORT MBC,SHOP C,GROCERY,27/08/2026,16.09.2026,0.00",
        'STOCKPORT MBC,SHOP D,GROCERY,27/08/2026,16.09.2026,"1,250.00"',
    ]
    raw = "\n".join(["AUGUST 2026,,,,,", ",,,,,", header, *bad]).encode("utf-8-sig")
    result = read_csv(raw, max_rows=100)
    assert [r.amount for r in result.rows] == [Decimal("1250.00")]
    reasons = {r.line: r.reason.lower() for r in result.rejected}
    assert "date" in reasons[4] and "amount" in reasons[5]
    assert "description" in reasons[6] and "zero" in reasons[7]
