"""
Unit tests for the rule-based categorizer.
"""

import pytest

from app.categorizer import (
    CATEGORY_BANK,
    CATEGORY_CLOUD,
    CATEGORY_HARDWARE,
    CATEGORY_INCOME,
    CATEGORY_MEALS,
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_PERSONAL,
    CATEGORY_REFUNDS,
    CATEGORY_SOFTWARE,
    CATEGORY_TRAVEL,
    categorize_batch,
    categorize_transaction,
    normalize_description,
)


class TestNormalize:
    def test_basic(self):
        assert normalize_description("  Adobe Creative Cloud  ") == "ADOBE CREATIVE CLOUD"

    def test_removes_stars_and_numbers(self):
        result = normalize_description("UBER *TRIP 12345678")
        assert "UBER" in result
        assert "TRIP" in result
        assert "12345678" not in result


class TestSoftware:
    def test_adobe(self):
        r = categorize_transaction("ADOBE CREATIVE CLOUD", -54.99)
        assert r.category == CATEGORY_SOFTWARE
        assert r.confidence == "high"

    def test_github(self):
        r = categorize_transaction("GITHUB.COM", -4.00)
        assert r.category == CATEGORY_SOFTWARE

    def test_vercel(self):
        r = categorize_transaction("VERCEL INC", -20.00)
        assert r.category == CATEGORY_SOFTWARE

    def test_openai(self):
        r = categorize_transaction("OPENAI *CHATGPT", -20.00)
        assert r.category == CATEGORY_SOFTWARE


class TestCloud:
    def test_aws(self):
        r = categorize_transaction("Amazon Web Services", -127.43)
        assert r.category == CATEGORY_CLOUD

    def test_digitalocean(self):
        r = categorize_transaction("DIGITALOCEAN.COM", -12.00)
        assert r.category == CATEGORY_CLOUD


class TestTravel:
    def test_uber(self):
        r = categorize_transaction("UBER *TRIP HELP.UBER.COM", -18.50)
        assert r.category == CATEGORY_TRAVEL

    def test_airbnb(self):
        r = categorize_transaction("AIRBNB * HM ABC123", -245.00)
        assert r.category == CATEGORY_TRAVEL


class TestRefundsAndIncome:
    def test_refund_positive_amount(self):
        r = categorize_transaction("ADOBE REFUND", 54.99)
        assert r.category == CATEGORY_REFUNDS
        assert r.confidence == "high"

    def test_refund_keyword_but_debit(self):
        # Suspicious – should go to Needs Review
        r = categorize_transaction("SOME REFUND FEE", -5.00)
        assert r.category == CATEGORY_NEEDS_REVIEW

    def test_stripe_income(self):
        r = categorize_transaction("STRIPE PAYOUT", 1250.00)
        assert r.category == CATEGORY_INCOME


class TestBank:
    def test_transfer(self):
        r = categorize_transaction("TRANSFER TO SAVINGS", -500.00)
        assert r.category == CATEGORY_BANK

    def test_wire_fee(self):
        r = categorize_transaction("WIRE TRANSFER FEE", -15.00)
        assert r.category == CATEGORY_BANK


class TestPersonal:
    def test_netflix(self):
        r = categorize_transaction("NETFLIX.COM", -15.99)
        assert r.category == CATEGORY_PERSONAL


class TestNeedsReview:
    def test_unknown_merchant(self):
        r = categorize_transaction("JOES CAFE 9921", -12.40)
        assert r.category == CATEGORY_NEEDS_REVIEW
        assert r.confidence == "low"

    def test_empty(self):
        r = categorize_transaction("", -10.00)
        assert r.category == CATEGORY_NEEDS_REVIEW


class TestBatch:
    def test_batch_categorization(self):
        txs = [
            {"date": "2025-01-02", "description": "GITHUB.COM", "amount": -4.00},
            {"date": "2025-01-03", "description": "JOES CAFE 9921", "amount": -9.50},
            {"date": "2025-01-04", "description": "STRIPE PAYOUT", "amount": 800.00},
        ]
        results = categorize_batch(txs)
        assert len(results) == 3
        assert results[0]["category"] == CATEGORY_SOFTWARE
        assert results[1]["category"] == CATEGORY_NEEDS_REVIEW
        assert results[2]["category"] == CATEGORY_INCOME
        assert "confidence" in results[0]
        assert "reason" in results[0]
