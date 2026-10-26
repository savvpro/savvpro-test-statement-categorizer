import pytest

from app.brain.categorizer import categorize
from app.services.summary import build_summary


@pytest.fixture
def categorized(make_txn, rules):
    txns = [
        make_txn("ADOBE CREATIVE CLOUD", -54.99),
        make_txn("UBER TRIP", -18.50),
        make_txn("TRANSFER TO SAVINGS", -500),
        make_txn("AMAZON REFUND", 29.99),
        make_txn("CLIENT PAYMENT ACME", 1200),
        make_txn("JOES CAFE", -12.40),
    ]
    return categorize(txns, rules)


def test_totals(categorized, rules):
    s = build_summary(categorized, rules)
    assert s.income == pytest.approx(1200)
    assert s.expenses == pytest.approx(73.49)
    assert s.refunds == pytest.approx(29.99)
    assert s.net_expenses == pytest.approx(43.50)  # refund kharche se minus
    assert s.needs_review_count == 1


def test_transfer_is_not_counted(categorized, rules):
    s = build_summary(categorized, rules)
    transfer = next(c for c in s.by_category if c.category == "Transfer (not spending)")
    assert transfer.counted is False
    assert s.expenses == pytest.approx(73.49)  # -500 shamil nahi


def test_refund_is_not_income(categorized, rules):
    s = build_summary(categorized, rules)
    assert s.income == pytest.approx(1200)  # 29.99 refund income mai nahi


def test_fixing_review_row_updates_totals(categorized, rules):
    joes = next(t for t in categorized if t.description == "JOES CAFE")
    joes.category = "Meals"
    s = build_summary(categorized, rules)
    assert s.needs_review_count == 0
    assert s.expenses == pytest.approx(85.89)


def test_ignored_duplicate_not_counted(categorized, rules):
    joes = next(t for t in categorized if t.description == "JOES CAFE")
    joes.category = "Duplicate (ignore)"
    s = build_summary(categorized, rules)
    assert s.expenses == pytest.approx(73.49)
    assert s.needs_review_count == 0