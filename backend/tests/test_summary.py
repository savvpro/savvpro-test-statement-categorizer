import datetime as dt
from decimal import Decimal

from app.models import CategorizedTransaction, Category, Split
from app.summary import build_summary


def tx(i, category, amount, splits=None, duplicate=False):
    return CategorizedTransaction(
        id=i, date=dt.date(2025, 1, 1), description="X", normalized="X",
        amount=Decimal(amount), category=category, confidence=0.9,
        explanation="test", is_duplicate=duplicate, splits=splits or [],
    )


def totals(summary):
    return {t.category: (t.total, t.count) for t in summary.totals}


def test_refund_reduces_the_expense():
    summary = build_summary([
        tx(1, Category.REPAIRS, "-340.00"),
        tx(2, Category.REPAIRS, "120.00"),  # refund
    ])
    assert totals(summary)[Category.REPAIRS] == (Decimal("-220.00"), 2)


def test_split_transaction_counts_its_parts_not_the_whole():
    payment = tx(
        1, Category.MORTGAGE_PAYMENT, "-1199.10",
        splits=[Split(category=Category.MORTGAGE_INTEREST, amount=Decimal("-1000.00")),
                Split(category=Category.MORTGAGE_PRINCIPAL, amount=Decimal("-199.10"))],
    )
    found = totals(build_summary([payment]))
    assert Category.MORTGAGE_PAYMENT not in found
    assert found[Category.MORTGAGE_INTEREST][0] == Decimal("-1000.00")
    assert found[Category.MORTGAGE_PRINCIPAL][0] == Decimal("-199.10")


def test_counts_and_empty_categories():
    summary = build_summary([
        tx(1, Category.NEEDS_REVIEW, "-5.00"),
        tx(2, Category.UTILITIES, "-9.00", duplicate=True),
    ])
    assert summary.transaction_count == 2
    assert summary.needs_review_count == 1
    assert summary.duplicate_count == 1
    assert {t.category for t in summary.totals} == {Category.NEEDS_REVIEW, Category.UTILITIES}


def test_empty_statement():
    summary = build_summary([])
    assert summary.totals == [] and summary.transaction_count == 0