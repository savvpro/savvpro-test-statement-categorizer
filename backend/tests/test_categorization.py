from app.services.categorization_engine import CategorizationEngine


def test_adobe_is_software():
    assert CategorizationEngine().categorize(
        "ADOBE CREATIVE CLOUD"
    )["category"] == "Software"


def test_uber_is_transportation():
    assert CategorizationEngine().categorize(
        "UBER TRIP"
    )["category"] == "Transportation"


def test_transfer_is_not_spending():
    result = CategorizationEngine().categorize("TRANSFER TO SAVINGS")
    assert result["category"] == "Transfer"
    assert result["exclude_from_spending"] is True


def test_refund_is_not_income():
    result = CategorizationEngine().categorize("REFUND AMAZON")
    assert result["category"] == "Refund"
    assert result["exclude_from_spending"] is True


def test_unknown_merchant_needs_review():
    result = CategorizationEngine().categorize("JOES CAFE 9921")
    assert result["category"] == "Needs Review"
    assert result["status"] == "needs_review"