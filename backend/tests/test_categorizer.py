import pytest
from app.categorizer import categorize_transaction
from app.models import Category, TransactionStatus


def test_software_categorization():
    decision = categorize_transaction("ADOBE CREATIVE CLOUD", -54.99)
    assert decision.category == Category.SOFTWARE
    assert decision.status == TransactionStatus.CATEGORIZED
    assert "Software vendor matched" in decision.matched_rule

    decision_gh = categorize_transaction("GITHUB *MEMBERSHIP", -21.00)
    assert decision_gh.category == Category.SOFTWARE


def test_travel_categorization():
    decision = categorize_transaction("UBER *TRIP DOWNTOWN", -28.45)
    assert decision.category == Category.TRAVEL
    assert decision.status == TransactionStatus.CATEGORIZED
    assert "Travel/transportation provider matched" in decision.matched_rule

    decision_air = categorize_transaction("DELTA AIRLINES 2940", -350.00)
    assert decision_air.category == Category.TRAVEL


def test_transfer_handling():
    # Transfers should be categorized as TRANSFER and not as general expenses
    decision = categorize_transaction("TRANSFER TO SAVINGS", -1000.00)
    assert decision.category == Category.TRANSFER
    assert decision.status == TransactionStatus.CATEGORIZED
    assert "Transfer pattern matched" in decision.matched_rule

    decision_inflow = categorize_transaction("WIRE TRANSFER FROM CHECKING", 500.00)
    assert decision_inflow.category == Category.TRANSFER


def test_refund_versus_income():
    # A refund is positive money returned, NOT income
    decision_refund = categorize_transaction("REFUND FROM AMAZON WEB SERVICES", 35.00)
    assert decision_refund.category == Category.REFUND
    assert decision_refund.status == TransactionStatus.CATEGORIZED
    assert "Refund indicator matched" in decision_refund.matched_rule
    assert decision_refund.category != Category.INCOME

    # Real income
    decision_income = categorize_transaction("STRIPE PAYOUT CLIENT INVOICE 1042", 3200.00)
    assert decision_income.category == Category.INCOME
    assert decision_income.status == TransactionStatus.CATEGORIZED
    assert "Business revenue pattern matched" in decision_income.matched_rule


def test_empty_or_whitespace_description():
    decision_empty = categorize_transaction("", -25.00)
    assert decision_empty.category == Category.NEEDS_REVIEW
    assert decision_empty.status == TransactionStatus.NEEDS_REVIEW
    assert decision_empty.confidence == 0.0

    decision_ws = categorize_transaction("   \t  ", -10.00)
    assert decision_ws.category == Category.NEEDS_REVIEW

    decision_na = categorize_transaction("N/A", -15.00)
    assert decision_na.category == Category.NEEDS_REVIEW


def test_unknown_descriptions():
    decision = categorize_transaction("RANDOM UNKNOWN CORNER STORE 9921", -45.00)
    assert decision.category == Category.NEEDS_REVIEW
    assert decision.status == TransactionStatus.NEEDS_REVIEW
    assert decision.confidence < 0.5


def test_ambiguous_retailer():
    # Multi-purpose retail (Amazon, Target, Walmart) should require review for business tax deductibility
    decision = categorize_transaction("AMAZON.COM*8B3120 RETAIL", -65.40)
    assert decision.category == Category.NEEDS_REVIEW
    assert "Multi-purpose vendor matched" in decision.matched_rule


def test_meals_and_office_supplies():
    decision_meals = categorize_transaction("STARBUCKS #0822", -6.50)
    assert decision_meals.category == Category.MEALS

    decision_supplies = categorize_transaction("STAPLES PRINTER PAPER", -34.50)
    assert decision_supplies.category == Category.OFFICE_SUPPLIES
