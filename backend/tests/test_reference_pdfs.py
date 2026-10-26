"""Real-world sample statements: parsed end to end and checked against their ground truth."""

from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.models import ParsedStatement, RawRow
from app.parsing.pdf_reader import read_pdf

REFERENCE = Path(__file__).resolve().parents[2] / "sample-data" / "reference"
BENCHMARK = REFERENCE / "bankstatemently-benchmark"
PARSER_SAMPLES = REFERENCE / "bank-statement-pdf-parser"

pytestmark = pytest.mark.skipif(not REFERENCE.exists(), reason="reference samples not present")

D = Decimal


@pytest.fixture(scope="module")
def parsed_cache() -> dict[Path, ParsedStatement]:
    return {}


@pytest.fixture(scope="module")
def parse(parsed_cache):
    def run(path: Path) -> ParsedStatement:
        if path not in parsed_cache:
            parsed_cache[path] = read_pdf(path.read_bytes(), max_rows=5000, max_pages=40)
        return parsed_cache[path]

    return run


def _signed(row: RawRow) -> Decimal:
    """Money in as positive, money out as negative, for rows with explicit direction."""
    return (row.credit or D(0)) - (row.debit or D(0))


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _assert_chain(rows: list[RawRow], opening: str, balances: list[str]) -> None:
    """Every row moves the running balance by exactly its amount, in the stated direction."""
    assert len(rows) == len(balances)
    running = D(opening)
    for row, balance in zip(rows, balances, strict=True):
        running += _signed(row)
        assert running == D(balance), f"line {row.line}: {row.description!r}"


# -- bank-statement-pdf-parser: ground truth in a CSV beside each PDF ------------------------

PARSER_NAMES = [
    "astra-premier-checking-jan-2026",
    "meridian-salary-account-feb-2026",
    "northstar-business-current-mar-2026",
]


def _expected_rows(name: str) -> list[dict[str, str]]:
    with (PARSER_SAMPLES / f"{name}.expected.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("name", PARSER_NAMES)
def test_indian_statements_match_the_expected_csv(parse, name):
    parsed = parse(PARSER_SAMPLES / f"{name}.pdf")
    expected = _expected_rows(name)

    assert len(parsed.rows) == len(expected)
    assert parsed.currency_hint == "INR"
    for row, truth in zip(parsed.rows, expected, strict=True):
        assert row.date == datetime.strptime(truth["date"], "%d-%m-%Y").date()
        withdrawal = D(truth["withdrawal"]) if truth["withdrawal"] else None
        deposit = D(truth["deposit"]) if truth["deposit"] else None
        assert row.debit == withdrawal and row.credit == deposit
        assert row.amount is None
        # The watermark letters must not leak into the narration.
        assert _squash(row.description) == _squash(truth["description"])


@pytest.mark.parametrize("name", PARSER_NAMES)
def test_indian_statements_follow_their_running_balance(parse, name):
    parsed = parse(PARSER_SAMPLES / f"{name}.pdf")
    expected = _expected_rows(name)
    balances = [truth["balance"] for truth in expected]
    first = expected[0]
    opening = D(first["balance"]) - (D(first["deposit"] or 0) - D(first["withdrawal"] or 0))
    _assert_chain(parsed.rows, str(opening), balances)


def test_indian_statements_report_no_stray_rejections(parse):
    for name in PARSER_NAMES:
        parsed = parse(PARSER_SAMPLES / f"{name}.pdf")
        assert not parsed.rejected


# -- bankstatemently-benchmark: counts and structure from the info JSON ------------------------

BENCHMARK_WINDOWS = {
    "bsb-001": (date(2025, 1, 1), date(2025, 1, 31)),
    "bsb-002": (date(2025, 9, 1), date(2025, 9, 30)),
    "bsb-003": (date(2025, 5, 1), date(2025, 5, 31)),
    "bsb-004": (date(2025, 9, 1), date(2025, 9, 30)),
    "bsb-005": (date(2025, 1, 1), date(2025, 1, 31)),
}
BENCHMARK_CURRENCY = {
    "bsb-001": "SGD",
    "bsb-002": "USD",
    "bsb-003": "EUR",
    "bsb-004": "HKD",
    "bsb-005": "CAD",
}


def _info(sample: str) -> dict:
    return json.loads((BENCHMARK / f"{sample}-statement-info.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("sample", sorted(BENCHMARK_WINDOWS))
def test_benchmark_statement_has_the_true_transaction_count(parse, sample):
    parsed = parse(BENCHMARK / f"{sample}-statement.pdf")
    assert len(parsed.rows) == _info(sample)["transactionCount"]


@pytest.mark.parametrize("sample", sorted(BENCHMARK_WINDOWS))
def test_benchmark_rows_are_well_formed(parse, sample):
    parsed = parse(BENCHMARK / f"{sample}-statement.pdf")
    start, end = BENCHMARK_WINDOWS[sample]
    assert parsed.currency_hint == BENCHMARK_CURRENCY[sample]
    for row in parsed.rows:
        assert start <= row.date <= end
        assert row.description.strip()
        values = [v for v in (row.debit, row.credit) if v is not None]
        assert all(v > 0 for v in values)
        assert (row.amount is None) != (not values), "either a signed amount or debit/credit"
    assert [r.date for r in parsed.rows] == sorted(r.date for r in parsed.rows)


def test_bsb001_separate_columns_and_multiline_cells(parse):
    parsed = parse(BENCHMARK / "bsb-001-statement.pdf")
    rows = parsed.rows
    _assert_chain(
        rows,
        "15450.75",
        [
            "17353.44", "17282.80", "17268.33", "17337.96", "17367.79", "16839.04",
            "16620.86", "16574.97", "16559.79", "16523.50", "15293.23", "15271.23",
        ],
    )  # fmt: skip
    assert sum(r.credit or D(0) for r in rows) == D("2002.15")
    assert sum(r.debit or D(0) for r in rows) == D("2181.67")
    # The wrapped lines of a cell are joined, the page-side watermark is not.
    first = rows[0].description
    assert first.startswith("Paynow from") and "PAYNOW TRANSFER 8373579" in first
    assert "Corp Holdings" in first
    assert all(r.currency == "SGD" for r in rows)


def test_bsb002_credit_card_keeps_printed_signs_and_trans_date(parse):
    parsed = parse(BENCHMARK / "bsb-002-statement.pdf")
    rows = parsed.rows
    assert all(r.amount is not None and r.debit is None and r.credit is None for r in rows)
    assert sum(r.amount for r in rows if r.amount > 0) == D("7699.43")  # "Purchases" in the summary
    assert sum(r.amount for r in rows if r.amount < 0) == D("-13.84")  # "Payment, Credits"
    redemption = next(r for r in rows if r.description.startswith("REWARDS REDEMPTION"))
    assert redemption.date == date(2025, 9, 11)  # Trans Date, not the 09/12 Post Date
    assert redemption.amount == D("-13.84")
    uber = rows[0]
    assert uber.description.startswith("UBER TRIP") and "775648" in uber.description
    # Zero-amount detail lines under a charge are not part of the merchant text.
    assert not any(
        "Chevron" in r.description or "Walmart Supercenter #" in r.description for r in rows
    )


def test_bsb003_dutch_dates_symbols_and_counterparty(parse):
    parsed = parse(BENCHMARK / "bsb-003-statement.pdf")
    rows = parsed.rows
    assert sum(r.amount for r in rows if r.amount > 0) == D("5983.38")
    assert sum(r.amount for r in rows if r.amount < 0) == D("-6628.42")
    first = rows[0]
    assert first.date == date(2025, 5, 1) and first.amount == D("114.83")
    assert "THOMAS DE GROOT" in first.description and "OVERBOEKING" in first.description
    big = next(r for r in rows if r.description.startswith("Bol.com"))
    assert big.amount == D("-1450.77") and big.date == date(2025, 5, 15)
    # The page footer sits on the same line as this row in the PDF.
    footer_row = next(r for r in rows if r.description.startswith("Vattenfall"))
    assert footer_row.amount == D("-19.40") and footer_row.date == date(2025, 5, 22)
    assert "rights" not in footer_row.description


def test_bsb004_two_account_tables(parse):
    parsed = parse(BENCHMARK / "bsb-004-statement.pdf")
    hkd = [r for r in parsed.rows if r.currency == "HKD"]
    usd = [r for r in parsed.rows if r.currency == "USD"]
    assert (len(hkd), len(usd)) == (15, 10)
    _assert_chain(
        hkd,
        "42580.00",
        [
            "42426.99", "40494.99", "40202.30", "40500.55", "39136.14", "38743.70", "32233.27",
            "27462.19", "27229.34", "27047.72", "23493.70", "18765.66", "19001.20", "18737.23",
            "18364.12",
        ],
    )  # fmt: skip
    _assert_chain(
        usd,
        "150000.00",
        [
            "149818.96", "150122.00", "138835.01", "138615.95", "173306.74", "173812.77",
            "169996.45", "169649.53", "170280.70", "170150.85",
        ],
    )  # fmt: skip
    assert hkd[0].description.startswith("Faster payment") and "Deliveroo" in hkd[0].description


def test_bsb005_french_dates_hidden_in_the_description(parse):
    parsed = parse(BENCHMARK / "bsb-005-statement.pdf")
    rows = parsed.rows
    assert rows[0].date == date(2025, 1, 2) and rows[0].description == "SKIP PLATS"
    assert rows[0].debit == D("151.30")
    assert rows[-1].date == date(2025, 1, 26) and rows[-1].description == "NETFLIX.COM"
    assert sum(r.credit or D(0) for r in rows) == D("7269.81")  # "Total Credits (7)"
    assert sum(r.debit or D(0) for r in rows) == D("6886.21")  # "Total Debits (18)"
    assert len([r for r in rows if r.credit]) == 7
    # 10 750,00 opening and 11 133,60 closing balance in the account summary.
    assert D("10750.00") + sum(_signed(r) for r in rows) == D("11133.60")
    thousands = next(r for r in rows if r.description == "AMAZON.CA")
    assert thousands.debit == D("1200.45")  # printed "1 200,45 $"
    assert not any("Frais" in r.description for r in rows)


def test_bsb005_balance_chain(parse):
    rows = parse(BENCHMARK / "bsb-005-statement.pdf").rows
    _assert_chain(
        rows,
        "10750.00",
        [
            "10598.70", "10609.03", "9408.58", "9509.73", "9480.04", "8938.77", "8226.57",
            "7902.95", "7314.68", "7295.98", "7195.70", "7227.16", "7261.13", "6693.34",
            "6759.98", "6675.00", "6800.28", "6727.36", "13628.34", "11732.54", "11643.58",
            "11590.08", "11572.82", "11150.71", "11133.60",
        ],
    )  # fmt: skip
