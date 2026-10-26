import pytest

from backend.app.engine import classify


@pytest.mark.parametrize(
    "description,category",
    [
        ("OPENAI CHATGPT SUBSCRIPTION", "AI & developer tools"),
        ("GITHUB COPILOT", "AI & developer tools"),
        ("ANTHROPIC CLAUDE AI", "AI & developer tools"),
        ("AWS", "Cloud & hosting"),
        ("NAMECHEAP", "Domains & websites"),
        ("NETFLIX", "Entertainment"),
        ("IMTIAZ", "Groceries"),
        ("NAYATEL", "Internet & mobile"),
        ("IESCO", "Utilities"),
        ("UDEMY", "Professional education"),
        ("SCHOOL TUITION", "Education"),
        ("CZONE MONITOR", "Equipment"),
        ("CAREEM", "Transport"),
        ("PHARMACY", "Healthcare"),
        ("EDHI DONATION", "Donations"),
    ],
)
def test_known_merchants(description, category):
    assert classify(description, 10000)["category"] == category


def test_recognition_does_not_prove_business_purpose():
    decision = classify("OPENAI CHATGPT", 568000)
    assert decision["category_confidence"] == "high"
    assert decision["purpose"] == "unknown"
    assert decision["needs_review"]
    assert decision["business_percent"] == 0


@pytest.mark.parametrize(
    "description,amount,kind",
    [
        ("PAYMENT THANK YOU", -10000000, "card_payment"),
        ("CREDIT CARD PAYMENT", 10000000, "card_payment"),
        ("TRANSFER TO OWN SAVINGS", 5000000, "transfer"),
        ("OPENAI REFUND", -284000, "refund"),
        ("OPENAI REFUND", 284000, "unresolved"),
        ("UNRECOGNIZED CREDIT", -5000, "unresolved"),
        ("ATM CASH WITHDRAWAL", 1500000, "cash"),
        ("INWARD REMITTANCE CLIENT ALPHA", -28000000, "income"),
    ],
)
def test_structural_types(description, amount, kind):
    assert classify(description, amount)["kind"] == kind


def test_family_cannot_be_inferred_from_ibft():
    decision = classify("IBFT TO RECIPIENT 001", 2500000)
    assert decision["category"] == "Transfer"
    assert decision["needs_review"]


def test_boundary_and_conflicting_matches():
    assert classify("PAWS PET STORE", 20000)["category"] == "Uncategorized"
    assert classify("NETFLIX NAYATEL", 20000)["rule_id"] == "conflict.merchant"


def test_user_rule_cannot_turn_refund_into_purchase():
    rule = {
        "match_text": "OPENAI REFUND",
        "kind": "expense",
        "category": "AI & developer tools",
        "purpose": "business",
        "business_percent": 100,
    }
    decision = classify("OPENAI REFUND", -284000, [rule])
    assert decision["kind"] == "refund"
    assert decision["needs_review"]
