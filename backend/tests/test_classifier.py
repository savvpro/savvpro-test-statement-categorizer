import pytest

from app.brain.categories import CARD_PAYMENT, INCOME, NEEDS_REVIEW, TRANSFER
from app.brain.classifier import Classifier
from app.domain.models import Flag


class FakeUserRules:
    def __init__(self, rules):
        self._rules = rules

    def get(self, key):
        return self._rules.get(key)


def decide(classifier, description, money_in=False):
    decision, _ = classifier.classify(description, money_in=money_in)
    return decision


@pytest.mark.parametrize(
    ("description", "category"),
    [
        ("ADOBE *CREATIVE CLOUD", "software"),
        ("FIGMA 1 YEAR PROFESSIONAL", "software"),
        ("UBER *TRIP HELP.UBER.COM", "travel"),
        ("UBER *EATS", "meals"),  # the longer phrase beats plain UBER
        ("AWS EMEA", "hosting"),
        ("AMAZON WEB SERVICES", "hosting"),  # beats the ambiguous AMAZON
        ("GOOGLE ADS 123456", "marketing"),  # beats the ambiguous GOOGLE
        ("WEWORK MEMBERSHIP", "rent"),
        ("NETFLIX.COM", "personal"),
        ("VERIZON WIRELESS", "telecom"),
        ("FOREIGN TRANSACTION FEE", "bank_fees"),
        ("INTEREST CHARGED ON PURCHASES", "bank_fees"),
        ("TRANSFER TO SAVINGS ****4421", TRANSFER),
        ("INTERNAL TRANSFER TO CHECKING", TRANSFER),
        ("AMEX EPAYMENT ACH PMT", CARD_PAYMENT),
    ],
)
def test_confident_decisions(classifier, description, category):
    decision = decide(classifier, description)
    assert decision.category_id == category
    assert decision.confidence >= 0.75


@pytest.mark.parametrize(
    "description",
    [
        "AMZN MKTP US*2K4PX0RT1",
        "AMAZON.COM",
        "WALMART SUPERCENTER",
        "SHELL OIL 57444",
        "ATM WITHDRAWAL 55821",
        "ZELLE PAYMENT TO ALEX",
        "APPLE.COM/BILL",
        "IRS USATAXPYMT",
        "GOOGLE *SERVICES",
    ],
)
def test_ambiguous_merchants_are_sent_to_review_with_candidates(classifier, description):
    decision = decide(classifier, description)
    assert decision.category_id == NEEDS_REVIEW
    assert Flag.AMBIGUOUS_MERCHANT in decision.flags
    assert len(decision.suggestions) >= 2
    assert "ambiguous" in decision.reasons[0]


def test_unknown_merchant_is_unknown_not_guessed(classifier):
    decision = decide(classifier, "UNKNOWN VENDOR 7731")
    assert decision.category_id == NEEDS_REVIEW
    assert decision.confidence == 0.0
    assert decision.suggestions == []


def test_generic_keyword_only_suggests(classifier):
    decision = decide(classifier, "SQ *JOES CAFE 9921")
    assert decision.category_id == NEEDS_REVIEW
    assert decision.suggestions == ["meals"]
    assert decision.confidence < 0.75
    assert "not recognised" in decision.reasons[0]


def test_transfer_to_a_person_is_not_assumed_to_be_own_account(classifier):
    decision = decide(classifier, "ONLINE TRANSFER TO JOHN SMITH")
    assert decision.category_id == NEEDS_REVIEW
    assert decision.suggestions == [TRANSFER]


def test_card_payment_in_is_not_income_or_refund(classifier):
    decision = decide(classifier, "ONLINE PAYMENT - THANK YOU", money_in=True)
    assert decision.category_id == CARD_PAYMENT
    assert not decision.refund_candidate


def test_refund_is_money_back_not_income(classifier):
    decision = decide(classifier, "ADOBE REFUND CREATIVE CLOUD", money_in=True)
    assert decision.refund_candidate
    assert Flag.REFUND in decision.flags
    assert decision.category_id == "software"
    assert decision.category_id != INCOME
    assert "refund" in decision.reasons[0].lower()


def test_money_in_from_unknown_source_is_never_called_income(classifier):
    decision = decide(classifier, "MYSTERY CREDIT 55", money_in=True)
    assert decision.category_id == NEEDS_REVIEW
    assert decision.refund_candidate


def test_client_payment_is_income(classifier):
    assert decide(classifier, "DEPOSIT CLIENT INVOICE 1042", money_in=True).category_id == INCOME
    assert decide(classifier, "STRIPE PAYOUT", money_in=True).category_id == INCOME


def test_bare_deposit_is_a_question_not_income(classifier):
    decision = decide(classifier, "DEPOSIT", money_in=True)
    assert decision.category_id == NEEDS_REVIEW
    assert decision.suggestions == [INCOME]


def test_user_rule_wins_over_builtin_rules(rule_table):
    classifier = Classifier(rule_table, FakeUserRules({"NETFLIX": "software"}))
    decision, _ = classifier.classify("NETFLIX.COM", money_in=False)
    assert decision.category_id == "software"
    assert decision.confidence == 1.0
    assert "saved" in decision.reasons[0]


def test_user_rule_with_unknown_category_is_ignored(rule_table):
    classifier = Classifier(rule_table, FakeUserRules({"NETFLIX": "gone"}))
    decision, _ = classifier.classify("NETFLIX.COM", money_in=False)
    assert decision.category_id == "personal"


def test_decisions_are_deterministic(classifier):
    first = decide(classifier, "AMZN MKTP US*2K4PX0RT1")
    second = decide(classifier, "AMZN MKTP US*2K4PX0RT1")
    assert first == second
