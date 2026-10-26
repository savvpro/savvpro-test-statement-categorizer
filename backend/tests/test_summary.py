import pytest
from app.models import Category, Transaction, TransactionStatus
from app.store import StatementStore


def create_test_tx(tx_id: str, amount: float, category: Category) -> Transaction:
    return Transaction(
        id=tx_id,
        date="2026-03-01",
        description="Test transaction",
        amount=amount,
        category=category,
        confidence=0.9,
        status=TransactionStatus.CATEGORIZED,
        matched_rule="Test rule",
        is_reviewed=False,
    )


def test_transfers_excluded_from_income_and_expenses():
    store = StatementStore()
    transactions = [
        create_test_tx("tx_1", 3000.0, Category.INCOME),
        create_test_tx("tx_2", -100.0, Category.SOFTWARE),
        create_test_tx("tx_3", -500.0, Category.TRANSFER),  # Transfer out
        create_test_tx("tx_4", 200.0, Category.TRANSFER),   # Transfer in
    ]
    summary = store.calculate_summary(transactions)

    # Transfers must NOT be counted into income or expenses
    assert summary.total_income == 3000.0
    assert summary.total_expenses == 100.0
    assert summary.transfers_count == 2
    assert summary.transfers_total == 700.0  # 500 + 200


def test_refund_offsets_expenses_not_income():
    store = StatementStore()
    transactions = [
        create_test_tx("tx_1", 2000.0, Category.INCOME),
        create_test_tx("tx_2", -300.0, Category.SOFTWARE),
        create_test_tx("tx_3", 50.0, Category.REFUND),  # Refund received
    ]
    summary = store.calculate_summary(transactions)

    assert summary.total_income == 2000.0
    assert summary.total_expenses == 300.0
    assert summary.total_refunds == 50.0
    # Net expenses should be reduced by the refund (300 - 50 = 250)
    assert summary.net_expenses == 250.0
    # Net cashflow = 2000 + 50 - 300 = 1750
    assert summary.net_cashflow == 1750.0


def test_needs_review_count():
    store = StatementStore()
    transactions = [
        create_test_tx("tx_1", -50.0, Category.NEEDS_REVIEW),
        create_test_tx("tx_2", -120.0, Category.NEEDS_REVIEW),
        create_test_tx("tx_3", -30.0, Category.MEALS),
    ]
    summary = store.calculate_summary(transactions)

    assert summary.needs_review_count == 2
    assert summary.total_transactions == 3
