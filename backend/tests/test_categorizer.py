from pathlib import Path

import pytest

from app.brain.categorizer import categorize, decide
from app.brain.result import INCOME, NEEDS_REVIEW, REFUND, TRANSFER
from app.parser.csv_parser import parse_csv

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data" / "fake_statement.csv"


def test_unknown_merchant_never_guessed(make_txn, rules):
    d = decide(make_txn("JOES CAFE", -12.4), rules)
    assert d.category == NEEDS_REVIEW
    assert d.confidence == "low"


def test_unknown_money_in_needs_review(make_txn, rules):
    d = decide(make_txn("MYSTERY DEPOSIT", 150), rules)
    assert d.category == NEEDS_REVIEW


def test_transfer_wins_over_keyword(make_txn, rules):
    d = decide(make_txn("TRANSFER TO ADOBE FUND", -10), rules)
    assert d.category == TRANSFER


def test_duplicate_is_flagged_not_dropped(make_txn, rules):
    a = make_txn("AMAZON REFUND", 29.99, row=6)
    b = make_txn("AMAZON REFUND", 29.99, row=7)
    result = categorize([a, b], rules)
    assert len(result) == 2  # kuch gayab nahi hua
    assert result[0].category == REFUND
    assert result[1].category == NEEDS_REVIEW
    assert "Possible duplicate of row 6" in result[1].reason


def test_same_amount_different_date_is_not_duplicate(make_txn, rules):
    a = make_txn("ADOBE CREATIVE CLOUD", -54.99, date="2026-10-01")
    b = make_txn("ADOBE CREATIVE CLOUD", -54.99, date="2026-11-01")
    result = categorize([a, b], rules)
    assert [t.category for t in result] == ["Software", "Software"]


def test_repeated_transfers_not_flagged_as_duplicates(make_txn, rules):
    a = make_txn("TRANSFER TO SAVINGS", -500)
    b = make_txn("TRANSFER TO SAVINGS", -500)
    result = categorize([a, b], rules)
    assert [t.category for t in result] == [TRANSFER, TRANSFER]


def test_tax_flag_is_set(make_txn, rules):
    result = categorize(
        [make_txn("ADOBE", -5), make_txn("STARBUCKS", -5), make_txn("JOES CAFE", -5)],
        rules,
    )
    assert [t.tax_deductible for t in result] == ["yes", "partial", "unknown"]


def test_every_row_gets_category_confidence_reason(make_txn, rules):
    result = categorize([make_txn("ADOBE", -5), make_txn("???", -1)], rules)
    for t in result:
        assert t.category and t.confidence and t.reason


# ---- poori sample file par ----
@pytest.fixture(scope="module")
def sample_result():
    from app.brain.rules_loader import load_rules

    txns, _ = parse_csv(SAMPLE.read_bytes())
    return categorize(txns, load_rules())


EXPECTED = {
    "ADOBE REFUND": REFUND,
    "ADOBE SYSTEMS": NEEDS_REVIEW,
    "AMAZON MKTP": NEEDS_REVIEW,
    "CANVA PRO": "Software",
    "CLIENT PAYMENT ACME": INCOME,
    "CLIENT PAYMENT GAMMA": INCOME,
    "CREDIT CARD PAYMENT THANK YOU": TRANSFER,
    "DELTA AIR LINES": "Travel",
    "DROPBOX": "Software",
    "FIGMA PROFESSIONAL": "Software",
    "GITHUB": "Software",
    "GOOGLE ADS": "Marketing",
    "INVOICE 1042 PAYMENT FROM BETA LLC": INCOME,
    "JOES CAFE 9921": NEEDS_REVIEW,
    "LYFT *RIDE 3321": "Travel",
    "MARRIOTT HOTEL": "Travel",
    "MYSTERY DEPOSIT": NEEDS_REVIEW,
    "NOTION LABS": "Software",
    "SHELL GAS STATION": NEEDS_REVIEW,
    "SLACK TECHNOLOGIES": "Software",
    "STAPLES": "Office",
    "STARBUCKS #4412": "Meals",
    "STRIPE PAYOUT": INCOME,
    "TRANSFER TO SAVINGS": TRANSFER,
    "UBER *TRIP 8821": "Travel",
    "UBER EATS 5521": "Meals",
    "VERIZON WIRELESS": "Internet & Phone",
    "WALMART SUPERCENTER": NEEDS_REVIEW,
    "ZOOM VIDEO COMMUNICATIONS": "Software",
}


@pytest.mark.parametrize("raw,expected", EXPECTED.items())
def test_sample_rows(sample_result, raw, expected):
    row = next(t for t in sample_result if t.raw_description == raw)
    assert row.category == expected


def test_sample_foreign_currency_row(sample_result):
    row = next(t for t in sample_result if t.currency == "EUR")
    assert row.category == NEEDS_REVIEW


def test_sample_recurring_adobe_is_not_duplicate(sample_result):
    usd = [
        t for t in sample_result
        if t.raw_description == "ADOBE CREATIVE CLOUD" and t.currency == "USD"
    ]
    assert len(usd) == 2
    assert all(t.category == "Software" for t in usd)


def test_sample_date_and_amount_formats(sample_result):
    github = next(t for t in sample_result if t.raw_description == "GITHUB")
    assert str(github.date) == "2026-10-25"
    slack = next(t for t in sample_result if t.raw_description == "SLACK TECHNOLOGIES")
    assert slack.amount == -8.75
    gamma = next(t for t in sample_result if t.raw_description == "CLIENT PAYMENT GAMMA")
    assert gamma.amount == 1200.0