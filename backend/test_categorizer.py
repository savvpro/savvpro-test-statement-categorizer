
from categorizer import categorize_transaction


def test_known_software_merchant():
    result = categorize_transaction("CLOUDHOST MONTHLY", -24.99)
    assert result["category"] == "Software"


def test_refund_is_not_income():
    result = categorize_transaction("SUPPLIER REFUND", 22.00)
    assert result["category"] == "Refund"


def test_transfer_is_not_spending():
    result = categorize_transaction("TRANSFER TO BUSINESS SAVINGS", -100.00)
    assert result["category"] == "Transfer - Not Spending"


def test_unknown_transaction_needs_review():
    result = categorize_transaction("UNKNOWN MERCHANT XYZ", -31.20)
    assert result["category"] == "Needs Review"


def test_unrecognized_positive_amount_needs_review():
    result = categorize_transaction("ONLINE ORDER PAYOUT", 350.00)
    assert result["category"] == "Needs Review"


def test_missing_description_needs_review():
    result = categorize_transaction("", -15.00)
    assert result["category"] == "Needs Review"


def test_matching_is_case_insensitive():
    result = categorize_transaction("cloudhost monthly", -24.99)
    assert result["category"] == "Software"
