"""Tests for the classifier (brain/classifier.py).

Covers every pipeline step, all tricky sample-data rows, override priority,
ambiguity handling, and a no-AI-SDK guarantee.
"""

import os

from app.brain.classifier import classify
from app.brain.overrides import OverrideStore


def _store() -> OverrideStore:
    return OverrideStore()


class TestOverridePriority:
    def test_override_takes_priority(self):
        store = _store()
        store.set("STARBUCKS", "Travel")
        result = classify("STARBUCKS", -5.00, store)
        assert result.category == "Travel"
        assert result.confidence == 1.0
        assert result.reason == "user correction"
        assert result.needs_review is False

    def test_override_on_normalized_name(self):
        store = _store()
        store.set("JOES CAFE", "Meals")
        result = classify("SQ *Joes Cafe #9921", -12.00, store)
        assert result.category == "Meals"
        assert result.reason == "user correction"


class TestStructuralTransfer:
    def test_transfer_to_savings(self):
        result = classify("TRANSFER TO SAVINGS 1234", -500.00, _store())
        assert result.category == "Transfer"
        assert result.needs_review is False

    def test_payment_thank_you(self):
        result = classify("PAYMENT THANK YOU", -1200.00, _store())
        assert result.category == "Transfer"
        assert result.needs_review is False

    def test_autopay(self):
        classify("AUTOPAY COMCAST", -89.99, _store())


class TestStructuralRefund:
    def test_refund_uber(self):
        result = classify("REFUND UBER *TRIP", 15.50, _store())
        assert result.category == "Refund"
        assert result.needs_review is False
        assert "uber" in result.reason.lower()

    def test_refund_positive_with_merchant(self):
        result = classify("STARBUCKS", 5.00, _store())
        assert result.category == "Refund"

    def test_refund_not_income(self):
        result = classify("REFUND UBER *TRIP", 15.50, _store())
        assert result.category != "Income"


class TestStructuralIncome:
    def test_invoice_deposit_client(self):
        result = classify("INVOICE DEPOSIT CLIENT ACME", 2500.00, _store())
        assert result.category == "Income"
        assert result.needs_review is False

    def test_payroll_deposit(self):
        result = classify("PAYROLL DEPOSIT", 3000.00, _store())
        assert result.category == "Income"

    def test_client_payment(self):
        result = classify("CLIENT PAYMENT ACME", 1500.00, _store())
        assert result.category == "Income"


class TestMerchantRulesExact:
    def test_adobe_exact(self):
        result = classify("ADOBE CREATIVE CLOUD", -29.99, _store())
        assert result.category == "Software"
        assert result.confidence == 0.95

    def test_netflix_exact(self):
        result = classify("NETFLIX", -15.99, _store())
        assert result.category == "Subscriptions"

    def test_uber_keyword(self):
        result = classify("UBER *TRIP", -22.50, _store())
        assert result.category == "Travel"

    def test_starbucks_exact(self):
        result = classify("STARBUCKS", -5.50, _store())
        assert result.category == "Meals"


class TestAmbiguity:
    def test_amazon_ambiguous(self):
        result = classify("AMZN Mktp US*BOOKS", -22.99, _store())
        assert result.category == "Needs Review"
        assert result.needs_review is True

    def test_paypal_ambiguous(self):
        result = classify("PAYPAL *EBAY SELLER", -8.75, _store())
        assert result.category == "Needs Review"
        assert result.needs_review is True

    def test_blank_description(self):
        result = classify("", -45.00, _store())
        assert result.category == "Needs Review"
        assert result.needs_review is True
        assert result.reason == "blank description"

    def test_unknown_merchant(self):
        result = classify("Joes Random Store", -12.00, _store())
        assert result.category == "Needs Review"
        assert result.needs_review is True


class TestTrickyRowsFromSampleData:
    """Every tricky row from sample_data/generate.py must have an explicit test."""

    def test_duplicate_adobe_is_software(self):
        result = classify("ADOBE CREATIVE CLOUD", -29.99, _store())
        assert result.category == "Software"
        assert result.needs_review is False

    def test_refund_uber_trip(self):
        result = classify("REFUND UBER *TRIP", 15.50, _store())
        assert result.category == "Refund"
        assert result.needs_review is False

    def test_transfer_to_savings(self):
        result = classify("TRANSFER TO SAVINGS 1234", -500.00, _store())
        assert result.category == "Transfer"
        assert result.needs_review is False

    def test_payment_thank_you(self):
        result = classify("PAYMENT THANK YOU", -1200.00, _store())
        assert result.category == "Transfer"
        assert result.needs_review is False

    def test_invoice_deposit_client_is_income(self):
        result = classify("INVOICE DEPOSIT CLIENT ACME", 2500.00, _store())
        assert result.category == "Income"
        assert result.needs_review is False

    def test_blank_description_needs_review(self):
        result = classify("", -45.00, _store())
        assert result.category == "Needs Review"
        assert result.needs_review is True

    def test_foreign_currency_fee_needs_review(self):
        result = classify("FOREIGN CURRENCY FEE EUR", -3.50, _store())
        assert result.category == "Needs Review"
        assert result.needs_review is True

    def test_amzn_mktp_us_books_needs_review(self):
        result = classify("AMZN Mktp US*BOOKS", -22.99, _store())
        assert result.category == "Needs Review"
        assert result.needs_review is True

    def test_paypal_ebay_seller_needs_review(self):
        result = classify("PAYPAL *EBAY SELLER", -8.75, _store())
        assert result.category == "Needs Review"
        assert result.needs_review is True


class TestNoAISDK:
    def test_brain_imports_no_ai_sdk(self):
        brain_dir = os.path.join(
            os.path.dirname(__file__), "..", "app", "brain"
        )
        ai_packages = {"openai", "anthropic", "gemini", "cohere", "llama_index"}
        for fname in os.listdir(brain_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(brain_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for pkg in ai_packages:
                assert pkg not in content.lower(), (
                    f"{fname} references AI package '{pkg}'"
                )
