import pytest

from backend.app.engine import classify


@pytest.mark.parametrize(
    "description,amount,category,kind,status",
    [
        ("ADOBE *CREATIVE CLOUD", -5999, "Software", "expense", "categorized"),
        ("FIGMA INC", -1500, "Software", "expense", "categorized"),
        ("AMAZON WEB SERVICES", -4218, "Software", "expense", "categorized"),
        ("UBER *TRIP", -1850, "Travel", "expense", "categorized"),
        ("UBER EATS", -1850, None, "expense", "needs_review"),
        ("SUPERUBER SOFTWARE", -1850, None, "expense", "needs_review"),
        ("GOOGLE ADS 1234", -12500, "Marketing", "expense", "categorized"),
        ("STRIPE PROCESSING FEE", -425, "Fees", "expense", "categorized"),
        ("TRANSFER TO SAVINGS", -50000, "Transfer", "transfer", "categorized"),
        ("CREDIT CARD PAYMENT", 50000, "Transfer", "transfer", "categorized"),
        ("UBER *TRIP REFUND", 1850, "Travel", "refund", "categorized"),
        ("UNKNOWN REFUND", 1850, None, "refund", "needs_review"),
        ("CLIENT PAYMENT FICTIONAL STUDIO", 120000, "Client income", "income", "categorized"),
        ("ADOBE", 1200, None, "credit", "needs_review"),
        ("REFUND ADOBE", -1200, None, "expense", "needs_review"),
        ("JOES CAFE 9921", -1275, None, "expense", "needs_review"),
        ("AMAZON MARKETPLACE", -2000, None, "expense", "needs_review"),
        ("SHELL SERVICE STATION", -6500, None, "expense", "needs_review"),
        ("PAYPAL TRANSFER CLIENT PAYMENT", 9000, None, "credit", "needs_review"),
    ],
)
def test_rules_are_conservative(description, amount, category, kind, status):
    decision = classify(description, amount)
    assert (decision.category, decision.kind, decision.status) == (category, kind, status)
    assert decision.reason
    assert decision.rule_id


def test_conflicting_merchant_rules_need_review():
    decision = classify("ADOBE UBER TRIP", -1000)
    assert decision.status == "needs_review"
    assert decision.category is None
