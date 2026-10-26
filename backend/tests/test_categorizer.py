from decimal import Decimal
from app.categorizer import categorize_transaction, clean_description, parse_amount


def test_known_software_subscription():
    result = categorize_transaction("ADOBE CREATIVE CLOUD", "-29.99")
    assert result["category"] == "Software & Subscriptions"
    assert result["confidence"] == "high"
    assert result["include_in_expenses"] is True
    assert result["is_tax_deductible"] is True


def test_figma_and_github():
    figma = categorize_transaction("FIGMA MONTHLY PRO", "-15.00")
    assert figma["category"] == "Software & Subscriptions"
    assert figma["confidence"] == "high"

    github = categorize_transaction("GITHUB *MEMBERSHIP", "-4.00")
    assert github["category"] == "Software & Subscriptions"
    assert github["confidence"] == "high"


def test_transfer_is_not_deductible():
    result = categorize_transaction("TRANSFER TO SAVINGS", "-500.00")
    assert result["category"] == "Transfer"
    assert result["confidence"] == "high"
    assert result["include_in_expenses"] is False
    assert result["is_tax_deductible"] is False


def test_credit_card_payment_is_transfer():
    result = categorize_transaction("AUTOPAY PAYMENT - THANK YOU", "-250.00")
    assert result["category"] == "Transfer"
    assert result["is_tax_deductible"] is False


def test_travel_expense():
    result = categorize_transaction("UBER *TRIP 8829", "-24.50")
    assert result["category"] == "Travel & Transit"
    assert result["confidence"] == "high"
    assert result["include_in_expenses"] is True


def test_meals_50_percent_deductible():
    result = categorize_transaction("STARBUCKS STORE 1042", "-6.75")
    assert result["category"] == "Meals (50% Deductible)"
    assert result["confidence"] == "high"


def test_unknown_merchant_needs_review():
    result = categorize_transaction("JOES CAFE 9921", "-12.00")
    assert result["category"] == "Needs Review"
    assert result["confidence"] == "low"
    assert "Unrecognized merchant" in result["reason"]


def test_refund_links_to_category_and_not_income():
    result = categorize_transaction("REFUND ADOBE CREATIVE CLOUD", "29.99")
    assert result["category"] == "Software & Subscriptions"
    assert result["transaction_type"] == "refund"
    assert result["include_in_expenses"] is False
    assert result["is_tax_deductible"] is False
    assert result["confidence"] == "high"


def test_refund_unknown_merchant_needs_review():
    result = categorize_transaction("REFUND UNKNOWN SHOP 123", "45.00")
    assert result["category"] == "Needs Review"
    assert result["transaction_type"] == "refund"
    assert result["confidence"] == "low"


def test_client_revenue_positive_amount():
    result = categorize_transaction("CLIENT PAYMENT INV-202", "1500.00")
    assert result["category"] == "Client Revenue"
    assert result["transaction_type"] == "income"
    assert result["confidence"] == "high"


def test_stripe_payout_positive_amount():
    result = categorize_transaction("STRIPE PAYOUT TRANSFER", "850.00")
    assert result["category"] == "Client Revenue"
    assert result["transaction_type"] == "income"


def test_unidentified_deposit_needs_review():
    result = categorize_transaction("CHECK DEPOSIT #8812", "300.00")
    assert result["category"] == "Needs Review"
    assert result["confidence"] == "low"
    assert "Incoming deposit detected" in result["reason"]


def test_accounting_parentheses_parsing():
    val = parse_amount("(49.99)")
    assert val == Decimal("-49.99")


def test_currency_symbol_and_commas():
    val = parse_amount("$1,250.50 USD")
    assert val == Decimal("1250.50")


def test_invalid_amount_returns_needs_review():
    result = categorize_transaction("ADOBE", "not-a-number")
    assert result["category"] == "Needs Review"
    assert result["confidence"] == "low"


def test_clean_description():
    assert clean_description("UBER   *TRIP #9921-X") == "UBER TRIP 9921 X"
