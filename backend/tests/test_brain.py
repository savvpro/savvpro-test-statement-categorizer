import pytest
from app.engine.brain import CategorizationBrain
from app.models.schemas import CategoryName, TaxDeductibility, TransactionType


def test_software_categorization():
    tx = CategorizationBrain.categorize_transaction(
        tx_id="1",
        date="2024-10-02",
        raw_description="ADOBE *CREATIVE CLOUD 800-833-6687 CA",
        amount=54.99
    )
    assert tx.category == CategoryName.SOFTWARE_SUBSCRIPTIONS
    assert tx.confidence >= 0.90
    assert not tx.needs_review
    assert tx.tax_status == TaxDeductibility.FULLY_DEDUCTIBLE


def test_travel_categorization():
    tx = CategorizationBrain.categorize_transaction(
        tx_id="2",
        date="2024-10-06",
        raw_description="UBER *TRIP HELP.UBER.COM",
        amount=34.20
    )
    assert tx.category == CategoryName.TRAVEL_RIDESHARE
    assert tx.confidence >= 0.90
    assert not tx.needs_review


def test_meals_50_percent_deductible():
    tx = CategorizationBrain.categorize_transaction(
        tx_id="3",
        date="2024-10-08",
        raw_description="STARBUCKS STORE #19821 SEATTLE WA",
        amount=6.75
    )
    assert tx.category == CategoryName.MEALS_ENTERTAINMENT
    assert tx.tax_status == TaxDeductibility.PARTIALLY_DEDUCTIBLE
    assert not tx.needs_review


def test_office_equipment():
    tx = CategorizationBrain.categorize_transaction(
        tx_id="4",
        date="2024-10-26",
        raw_description="BEST BUY #0491 SAN FRANCISCO CA",
        amount=189.99
    )
    assert tx.category == CategoryName.OFFICE_EQUIPMENT
    assert tx.tax_status == TaxDeductibility.FULLY_DEDUCTIBLE
