import pytest
from app.engine.brain import CategorizationBrain
from app.engine.memory import user_rule_memory
from app.models.schemas import CategoryName, TaxDeductibility, TransactionType


def test_task_example_adobe():
    """TASK.md: 'ADOBE CREATIVE CLOUD becomes Software'"""
    tx = CategorizationBrain.categorize_transaction(
        tx_id="tx-adobe",
        date="2024-10-02",
        raw_description="ADOBE CREATIVE CLOUD",
        amount=54.99
    )
    assert tx.category == CategoryName.SOFTWARE_SUBSCRIPTIONS
    assert not tx.needs_review


def test_task_example_uber():
    """TASK.md: 'UBER *TRIP becomes Travel'"""
    tx = CategorizationBrain.categorize_transaction(
        tx_id="tx-uber",
        date="2024-10-06",
        raw_description="UBER *TRIP",
        amount=34.20
    )
    assert tx.category == CategoryName.TRAVEL_RIDESHARE
    assert not tx.needs_review


def test_task_example_transfer_to_savings():
    """TASK.md: 'TRANSFER TO SAVINGS is not spending'"""
    tx = CategorizationBrain.categorize_transaction(
        tx_id="tx-transfer",
        date="2024-10-15",
        raw_description="TRANSFER TO SAVINGS ACC #4821",
        amount=1000.00
    )
    assert tx.category == CategoryName.INTERNAL_TRANSFER
    assert tx.tax_status == TaxDeductibility.NON_DEDUCTIBLE
    assert not tx.needs_review


def test_task_example_unknown_joes_cafe():
    """TASK.md: 'JOES CAFE 9921 is unknown, so it goes to Needs Review'"""
    tx = CategorizationBrain.categorize_transaction(
        tx_id="tx-unknown",
        date="2024-10-10",
        raw_description="JOES CAFE 9921",
        amount=14.50
    )
    assert tx.category == CategoryName.NEEDS_REVIEW
    assert tx.needs_review is True
    assert "Unrecognized merchant" in tx.review_reason or "Needs Review" in tx.category.value


def test_refund_is_money_back_not_income():
    """TASK.md: 'a refund is money back, not income'"""
    tx = CategorizationBrain.categorize_transaction(
        tx_id="tx-refund",
        date="2024-10-17",
        raw_description="REFUND: APPLE STORE RETURN #9812",
        amount=-129.00,
        tx_type=TransactionType.CREDIT
    )
    assert tx.category == CategoryName.REFUND_CREDIT
    assert tx.tax_status == TaxDeductibility.EXPENSE_OFFSET
    assert not tx.needs_review
    assert tx.category != CategoryName.GROSS_INCOME


def test_income_client_invoice():
    """Gross income detection for business revenue"""
    tx = CategorizationBrain.categorize_transaction(
        tx_id="tx-income",
        date="2024-10-12",
        raw_description="CLIENT INVOICE #1042 WIRE TRANSFER INCOMING",
        amount=-3500.00,
        tx_type=TransactionType.CREDIT
    )
    assert tx.category == CategoryName.GROSS_INCOME
    assert tx.tax_status == TaxDeductibility.TAXABLE_INCOME
    assert not tx.needs_review


def test_user_override_feedback_loop():
    """When user fixes a Needs Review row, brain remembers it for future occurrences"""
    # 1. Unknown merchant initially triggers Needs Review
    unknown_tx = CategorizationBrain.categorize_transaction(
        tx_id="tx-custom",
        date="2024-10-24",
        raw_description="LOCAL PRINT SHOP 881",
        amount=45.00
    )
    assert unknown_tx.needs_review is True

    # 2. User overrides merchant category
    user_rule_memory.add_override(
        clean_merchant=unknown_tx.clean_merchant,
        category=CategoryName.MARKETING_ADVERTISING
    )

    # 3. Next time the same merchant appears, brain auto-categorizes with 1.0 confidence!
    re_categorized = CategorizationBrain.categorize_transaction(
        tx_id="tx-custom-2",
        date="2024-10-25",
        raw_description="LOCAL PRINT SHOP 881",
        amount=60.00
    )
    assert re_categorized.category == CategoryName.MARKETING_ADVERTISING
    assert re_categorized.needs_review is False
    assert re_categorized.confidence == 1.0
