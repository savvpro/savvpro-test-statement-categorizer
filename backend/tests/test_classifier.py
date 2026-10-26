"""
Unit tests for deterministic 3-tier StatementBrain classifier.
"""

import pytest
from app.brain.classifier import StatementBrain
from app.models.transaction import TransactionRaw, TransactionDirection, ReviewStatus


@pytest.fixture
def brain():
    return StatementBrain()


def test_classify_tier1_software(brain):
    tx = TransactionRaw(id="1", date="2024-10-01", raw_description="GITHUB INC", amount=-25.0)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Software & Subscriptions"
    assert cat.confidence >= 0.95
    assert not cat.needs_review
    assert cat.status == ReviewStatus.AUTO_VERIFIED
    assert cat.tax_deductible is True
    assert cat.deductible_percentage == 1.0
    assert cat.deductible_amount == 25.0


def test_classify_tier1_travel(brain):
    tx = TransactionRaw(id="2", date="2024-10-04", raw_description="UBER *TRIP HELP.UBER.COM", amount=-32.50)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Travel & Transportation"
    assert cat.confidence >= 0.95
    assert not cat.needs_review


def test_classify_tier1_utilities(brain):
    tx = TransactionRaw(id="3", date="2024-10-06", raw_description="COMCAST CABLE COMM", amount=-89.99)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Internet & Utilities"
    assert cat.confidence >= 0.95
    assert cat.deductible_percentage == 0.8
    assert cat.deductible_amount == round(89.99 * 0.8, 2)


def test_classify_tier2_amazon_mixed_use(brain):
    tx = TransactionRaw(id="4", date="2024-10-09", raw_description="SQ *AMZN MKTP US*2B71X99", amount=-89.99)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Office Supplies & Books"
    assert cat.needs_review is True
    assert cat.status == ReviewStatus.NEEDS_REVIEW
    assert "personal" in cat.review_reason.lower()


def test_classify_tier2_apple_mixed_use(brain):
    tx = TransactionRaw(id="5", date="2024-10-09", raw_description="APPLE.COM/BILL", amount=-1299.0)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Hardware & Equipment"
    assert cat.needs_review is True


def test_classify_tier2_target_mixed_use(brain):
    tx = TransactionRaw(id="6", date="2024-10-10", raw_description="TARGET 02841", amount=-45.67)
    cat = brain.categorize_transaction(tx)
    assert cat.needs_review is True


def test_classify_tier3_auto_verified_meal_chain(brain):
    tx = TransactionRaw(id="7", date="2024-10-11", raw_description="STARBUCKS STORE 18294", amount=-6.45)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Meals & Client Entertainment"
    assert not cat.needs_review
    assert cat.deductible_percentage == 0.5
    assert cat.deductible_amount == round(6.45 * 0.5, 2)


def test_classify_tier3_unknown_local_cafe_needs_review(brain):
    tx = TransactionRaw(id="8", date="2024-10-12", raw_description="JOES CAFE 9921", amount=-22.0)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Meals & Client Entertainment"
    assert cat.needs_review is True
    assert cat.status == ReviewStatus.NEEDS_REVIEW


def test_classify_transfer_non_taxable(brain):
    tx = TransactionRaw(id="9", date="2024-10-14", raw_description="TRANSFER TO SAVINGS", amount=-500.0)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Transfers & Non-Taxable"
    assert not cat.needs_review
    assert cat.tax_deductible is False
    assert cat.deductible_amount == 0.0


def test_classify_stripe_payout_income(brain):
    tx = TransactionRaw(id="10", date="2024-10-15", raw_description="STRIPE PAYOUT", amount=8500.0)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Gross Business Income"
    assert cat.direction == TransactionDirection.INFLOW
    assert not cat.needs_review


def test_classify_refund(brain):
    tx = TransactionRaw(id="11", date="2024-10-13", raw_description="REFUND AMAZON MKTP", amount=89.99)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Refund / Expense Reduction"
    assert cat.direction == TransactionDirection.REFUND
    assert not cat.needs_review


def test_classify_unrecognized_fallback(brain):
    tx = TransactionRaw(id="12", date="2024-10-17", raw_description="RANDOM MERCHANT XYZ 88192", amount=-55.0)
    cat = brain.categorize_transaction(tx)
    assert cat.category == "Needs Review"
    assert cat.confidence <= 0.30
    assert cat.needs_review is True
