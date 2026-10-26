from dataclasses import replace

import pytest
from statement_categorizer.domain import Category, Kind, ParsedTransaction
from statement_categorizer.engine import MerchantRule, categorize, normalize


def transaction(description, amount=-1000):
    return ParsedTransaction(2, "2026-04-02", description, amount, "USD")


@pytest.mark.parametrize(
    ("description", "category"),
    [
        ("ADOBE CREATIVE CLOUD", Category.SOFTWARE),
        ("FIGMA*PROFESSIONAL 12345", Category.SOFTWARE),
        ("github inc", Category.SOFTWARE),
        ("UBER *TRIP HELP.UBER.COM", Category.TRAVEL),
        ("LYFT RIDE 38294", Category.TRAVEL),
        ("GOOGLE ADS 123", Category.MARKETING),
        ("META ADS 456", Category.MARKETING),
        ("MONTHLY ACCOUNT FEE", Category.FEES),
        ("WIRE TRANSFER FEE", Category.FEES),
    ],
)
def test_known_expenses_have_explanations(description, category):
    decision = categorize(transaction(description))
    assert decision.category == category
    assert decision.kind == Kind.EXPENSE
    assert not decision.needs_review
    assert decision.rule_id and decision.reason and decision.confidence >= 0.9


@pytest.mark.parametrize(
    "description",
    ["TRANSFER TO SAVINGS", "TRANSFER FROM SAVINGS", "CREDIT CARD PAYMENT", "PAYMENT THANK YOU", "INTERNAL TRANSFER"],
)
@pytest.mark.parametrize("amount", [-1000, 1000])
def test_transfers_never_become_spending_or_income(description, amount):
    decision = categorize(transaction(description, amount))
    assert decision.kind == Kind.TRANSFER
    assert decision.category == Category.TRANSFERS


@pytest.mark.parametrize("description", ["ADOBE REFUND", "REFUND ADOBE CREATIVE CLOUD", "FIGMA RETURNED"])
def test_explicit_refunds_reduce_original_category(description):
    decision = categorize(transaction(description, 1200))
    assert decision.kind == Kind.REFUND
    assert decision.category == Category.SOFTWARE
    assert not decision.needs_review


@pytest.mark.parametrize(
    "description",
    [
        "JOES CAFE 9921",
        "AMAZON MARKETPLACE",
        "PAYPAL *UNKNOWN",
        "APPLE.COM/BILL",
        "ADOBESCAM",
        "SUBWAY",
        "UBER",
        "GOOGLE CLOUD",
        "PERSONAL ADOBE",
    ],
)
def test_broad_or_unknown_merchants_abstain(description):
    decision = categorize(transaction(description))
    assert decision.needs_review
    assert decision.category == Category.REVIEW


@pytest.mark.parametrize("description", ["ADOBE", "CLIENT PAYMENT DEMO STUDIO", "BANK DEPOSIT"])
def test_credit_is_not_automatically_income_or_refund(description):
    decision = categorize(transaction(description, 1000))
    assert decision.needs_review and decision.kind == Kind.UNKNOWN


def test_transfer_wording_without_own_account_evidence_abstains():
    assert categorize(transaction("TRANSFER FROM CLIENT DEMO", 10000)).needs_review
    assert categorize(transaction("TRANSFER TO CONTRACTOR DEMO", -10000)).needs_review


def test_uber_eats_is_not_travel_and_requires_business_purpose():
    decision = categorize(transaction("UBER EATS"))
    assert decision.category == Category.MEALS
    assert decision.needs_review


@pytest.mark.parametrize(
    "description",
    ["ADOBE CHARGEBACK", "CASHBACK REWARD", "ADOBE REVERSAL", "ATM CASH WITHDRAWAL", "ADOBE...", "ADOBE…"],
)
def test_special_cases_require_review(description):
    assert categorize(transaction(description)).needs_review


def test_unknown_refund_and_conflicting_sign():
    decision = categorize(transaction("REFUND UNKNOWN", 1000))
    assert decision.kind == Kind.REFUND and decision.needs_review
    assert categorize(transaction("ADOBE REFUND", -1000)).rule_id == "review.sign"
    assert categorize(transaction("FIGMA", 0)).rule_id == "review.zero"


def test_rules_that_disagree_abstain(monkeypatch):
    from statement_categorizer import engine

    first = MerchantRule("test.one", "^COLLISION", Category.SOFTWARE, 0.99, "one")
    monkeypatch.setattr(engine, "MERCHANT_RULES", (first, replace(first, id="test.two", category=Category.TRAVEL)))
    assert engine.categorize(transaction("COLLISION")).rule_id == "review.conflict"


def test_normalization_and_determinism():
    assert normalize("  ＡＤＯＢＥ * creative\ncloud 123 ") == "ADOBE CREATIVE CLOUD 123"
    tx = transaction("FIGMA * 123")
    assert [categorize(tx) for _ in range(10)] == [categorize(tx)] * 10
