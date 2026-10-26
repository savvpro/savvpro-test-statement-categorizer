
from app.categorizer import categorize_transaction


def test_known_software_merchant():
    result = categorize_transaction("GitHub subscription", -10.00)
    assert result["category"] == "Software & Subscriptions"


def test_transfer_is_not_spending():
    result = categorize_transaction("Account transfer", -100.00)
    assert result["category"] == "Transfer"


def test_refund_is_not_income():
    result = categorize_transaction("Adobe refund", 25.00)
    assert result["category"] == "Refund"


def test_unknown_transaction_needs_review():
    result = categorize_transaction("Unknown merchant 123", -42.00)
    assert result["category"] == "Needs Review"
    assert result["status"] == "Needs Review"
