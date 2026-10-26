import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

from app.brain.models import AccountType
from app.parsing import parse_statement

REPO = Path(__file__).resolve().parents[3]
SAMPLES = REPO / "samples"


def load_generator():  # type: ignore[no-untyped-def]
    path = REPO / "backend" / "scripts" / "make_samples.py"
    spec = importlib.util.spec_from_file_location("make_samples", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# name, account type, rows, errors, pending, sign convention, money in, money out
EXPECTED = [
    ("checking_simple.csv", "checking", 45, 0, 0, "as_is", "27217.08", "-13320.53"),
    ("credit_card.csv", "credit_card", 50, 0, 0, "charges_positive", "5250.55", "-2553.20"),
    ("bank_messy.csv", "checking", 14, 1, 1, "debit_credit_columns", "9222.42", "-5624.71"),
    ("credit_card.xlsx", "credit_card", 25, 0, 0, "charges_negative", "5190.55", "-1752.48"),
]


@pytest.mark.parametrize(
    ("name", "account", "rows", "errors", "pending", "convention", "money_in", "money_out"),
    EXPECTED,
)
def test_sample_parses(
    name: str,
    account: str,
    rows: int,
    errors: int,
    pending: int,
    convention: str,
    money_in: str,
    money_out: str,
) -> None:
    result = parse_statement((SAMPLES / name).read_bytes(), name, AccountType(account))

    assert len(result.rows) == rows
    assert len(result.errors) == errors
    assert sum(r.is_pending for r in result.rows) == pending
    assert result.detected.sign_convention == convention
    assert sum((r.amount for r in result.rows if r.amount > 0), Decimal(0)) == Decimal(money_in)
    assert sum((r.amount for r in result.rows if r.amount < 0), Decimal(0)) == Decimal(money_out)
    assert all(r.date.year == 2026 and 1 <= r.date.month <= 3 for r in result.rows)


def test_messy_sample_details() -> None:
    result = parse_statement(
        (SAMPLES / "bank_messy.csv").read_bytes(), "m.csv", AccountType.checking
    )

    assert result.detected.encoding == "utf-8-sig"
    assert result.detected.delimiter == ";"
    assert result.detected.header_line == 4
    assert [(e.line_no, e.reason) for e in result.errors] == [(13, "invalid date '31 Feb 2026'")]
    assert result.warnings == [
        "line 5: skipped summary row 'OPENING BALANCE'",
        "line 24: skipped summary row 'TOTAL'",
    ]
    pending = next(r for r in result.rows if r.is_pending)
    assert pending.description == "UBER *TRIP HELP.UBER.COM"
    assert pending.amount == Decimal("-24.60")


def test_card_csv_keeps_exact_duplicate() -> None:
    result = parse_statement(
        (SAMPLES / "credit_card.csv").read_bytes(), "c.csv", AccountType.credit_card
    )
    joes = [(r.date, r.amount) for r in result.rows if r.description == "SQ *JOES CAFE 9921"]

    assert len(joes) == 3
    assert joes[1] == joes[2]


def test_committed_samples_match_generator(tmp_path: Path) -> None:
    for path in load_generator().write_samples(tmp_path):
        assert path.read_bytes() == (SAMPLES / path.name).read_bytes(), path.name
