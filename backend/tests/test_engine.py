import pytest

from app.engine import Rule, classify, normalize


@pytest.mark.parametrize(
    "text,amount,kind,category,status",
    [
        ("ADOBE CREATIVE CLOUD", -3200, "expense", "software", "categorized"),
        ("  adobe   CREATIVE cloud  ", -3200, "expense", "software", "categorized"),
        ("ADOBE CREATIVE CLOUD REFUND", 1200, "refund", "software", "categorized"),
        ("UNKNOWN STORE REFUND", 1200, "refund", "uncategorized", "needs_review"),
        ("TRANSFER TO SAVINGS", -10000, "transfer", "transfers", "categorized"),
        ("TRANSFER FROM SAVINGS", 10000, "transfer", "transfers", "categorized"),
        ("CLIENT INVOICE PAYMENT", 50000, "income", "income", "categorized"),
        ("ADOBE CREATIVE CLOUD", 3200, "unknown", "uncategorized", "needs_review"),
        ("PAYMENT", -500, "expense", "uncategorized", "needs_review"),
        ("JOES CAFE 9921", -500, "expense", "uncategorized", "needs_review"),
        ("UBER *TRIP", -500, "expense", "travel", "needs_review"),
        ("UBER EATS", -500, "expense", "meals", "needs_review"),
        ("FIGMATIC SERVICES", -500, "expense", "uncategorized", "needs_review"),
        ("FIGMA", 0, "unknown", "uncategorized", "needs_review"),
        ("REFUND FIGMA", -100, "unknown", "uncategorized", "needs_review"),
        ("INTERNAL TRANSFER REFUND", 100, "unknown", "uncategorized", "needs_review"),
        ("INTERNAL TRANSFER FIGMA", -100, "unknown", "uncategorized", "needs_review"),
        ("GITHUB GOOGLE ADS", -100, "expense", "uncategorized", "needs_review"),
    ],
)
def test_decisions(text, amount, kind, category, status):
    decision = classify(text, amount)
    assert (decision.kind, decision.category, decision.status) == (kind, category, status)
    assert decision.explanation
    if status == "categorized":
        assert decision.rule_ids and decision.evidence


def test_rule_order_does_not_resolve_conflict():
    a = Rule("a", "software", ("acme",))
    b = Rule("b", "marketing", ("acme",))
    assert classify("ACME", -500, (a, b)) == classify("ACME", -500, (b, a))
    assert classify("ACME", -500, (a, b)).reason == "conflicting_rules"


@pytest.mark.parametrize("description", ["FIGMA", "figma", "  Figma  ", "ＦＩＧＭＡ"])
def test_normalization_stability(description):
    assert normalize(description) == "figma"
    assert classify(description, -429).category == "software"


def test_amount_is_not_merchant_evidence():
    assert classify("Unseen vendor", -9900).status == "needs_review"
    assert classify("Unseen vendor", -12345).status == "needs_review"
