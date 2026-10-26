"""Tests for the brain pipeline – normalization, each stage, and end-to-end."""

from __future__ import annotations

from datetime import date

import pytest

from app.brain.categories import CATEGORIES, CategoryType
from app.brain.dictionary import check_dictionary
from app.brain.keywords import check_keywords
from app.brain.normalize import (
    NormalizedRow,
    compute_fingerprint,
    normalize_description,
    parse_amount_cents,
)
from app.brain.pipeline import BrainResult, UserRuleSpec, run_pipeline
from app.brain.refunds import check_refund
from app.brain.scoring import apply_scoring, determine_status
from app.brain.transfers import check_exclusions


# ═══════════════════════════════════════════════════════════════════════════
# Stage 0: Normalize
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalize:
    def test_strip_processor_prefix_sq(self):
        assert normalize_description("SQ *JOES CAFE") == "JOES CAFE"

    def test_strip_processor_prefix_paypal(self):
        assert normalize_description("PAYPAL *JOHNDOE") == "JOHNDOE"

    def test_strip_processor_prefix_amzn(self):
        result = normalize_description("AMZN MKTP US 3K1F2")
        assert result == "AMAZON"

    def test_strip_noise_pos(self):
        result = normalize_description("POS STARBUCKS 1234")
        assert "POS" not in result
        assert "STARBUCKS" in result

    def test_strip_noise_checkcard(self):
        result = normalize_description("CHECKCARD 0108 STAPLES #1234")
        assert "CHECKCARD" not in result
        assert "STAPLES" in result

    def test_strip_trailing_date(self):
        result = normalize_description("UBER TRIP 01/15")
        assert "01/15" not in result
        assert "UBER" in result

    def test_uppercase(self):
        assert normalize_description("adobe creative cloud") == "ADOBE CREATIVE CLOUD"

    def test_collapse_whitespace(self):
        result = normalize_description("ADOBE   CREATIVE    CLOUD")
        assert "  " not in result


class TestParseAmountCents:
    def test_simple_positive(self):
        assert parse_amount_cents("59.99") == 5999

    def test_simple_negative(self):
        assert parse_amount_cents("-59.99") == -5999

    def test_dollar_sign(self):
        assert parse_amount_cents("$1,234.56") == 123456

    def test_parenthesized_negative(self):
        assert parse_amount_cents("(123.45)") == -12345

    def test_dr_marker(self):
        assert parse_amount_cents("59.99 DR") == -5999

    def test_empty(self):
        assert parse_amount_cents("") == 0
        assert parse_amount_cents(None) == 0

    def test_separate_columns(self):
        assert parse_amount_cents(None, debit_value="100.00", credit_value="") == -10000
        assert parse_amount_cents(None, debit_value="", credit_value="50.00") == 5000

    def test_no_decimal(self):
        assert parse_amount_cents("100") == 10000


class TestFingerprint:
    def test_same_input_same_hash(self):
        fp1 = compute_fingerprint(date(2026, 1, 4), "ADOBE", -5999)
        fp2 = compute_fingerprint(date(2026, 1, 4), "ADOBE", -5999)
        assert fp1 == fp2

    def test_different_input_different_hash(self):
        fp1 = compute_fingerprint(date(2026, 1, 4), "ADOBE", -5999)
        fp2 = compute_fingerprint(date(2026, 1, 5), "ADOBE", -5999)
        assert fp1 != fp2


# ═══════════════════════════════════════════════════════════════════════════
# Stage 1: Exclusions
# ═══════════════════════════════════════════════════════════════════════════

class TestExclusions:
    def _row(self, desc: str, amount: int = -1000) -> NormalizedRow:
        return NormalizedRow(
            row_index=0,
            posted_date=date(2026, 1, 1),
            raw_description=desc,
            merchant_key=normalize_description(desc),
            amount_cents=amount,
        )

    def test_cc_payment(self):
        p = check_exclusions(self._row("PAYMENT THANK YOU"))
        assert p is not None
        assert p.category == "credit_card_payment"

    def test_transfer(self):
        p = check_exclusions(self._row("ONLINE TRANSFER TO SAVINGS"))
        assert p is not None
        assert p.category == "transfer"

    def test_zelle_self(self):
        p = check_exclusions(self._row("ZELLE TO SELF"))
        assert p is not None
        assert p.category == "transfer"

    def test_atm(self):
        p = check_exclusions(self._row("ATM WITHDRAWAL"))
        assert p is not None
        assert p.category == "needs_review"
        assert "atm_withdrawal" in p.flags

    def test_normal_merchant(self):
        p = check_exclusions(self._row("ADOBE CREATIVE CLOUD"))
        assert p is None


# ═══════════════════════════════════════════════════════════════════════════
# Stage 3: Dictionary
# ═══════════════════════════════════════════════════════════════════════════

class TestDictionary:
    def _row(self, key: str) -> NormalizedRow:
        return NormalizedRow(
            row_index=0,
            posted_date=date(2026, 1, 1),
            raw_description=key,
            merchant_key=key,
            amount_cents=-5999,
        )

    def test_exact_match_adobe(self):
        p = check_dictionary(self._row("ADOBE"))
        assert p is not None
        assert p.category == "software_subscriptions"
        assert p.confidence >= 0.95

    def test_exact_match_google_ads(self):
        p = check_dictionary(self._row("GOOGLE ADS"))
        assert p is not None
        assert p.category == "advertising"

    def test_mixed_use_amazon(self):
        p = check_dictionary(self._row("AMAZON"))
        assert p is not None
        assert p.confidence <= 0.50
        assert "mixed_use_merchant" in p.flags

    def test_no_match(self):
        p = check_dictionary(self._row("XYZNONEXISTENT"))
        assert p is None


# ═══════════════════════════════════════════════════════════════════════════
# Stage 4: Keywords
# ═══════════════════════════════════════════════════════════════════════════

class TestKeywords:
    def _row(self, desc: str) -> NormalizedRow:
        return NormalizedRow(
            row_index=0,
            posted_date=date(2026, 1, 1),
            raw_description=desc,
            merchant_key=normalize_description(desc),
            amount_cents=-1000,
        )

    def test_restaurant_keyword(self):
        p = check_keywords(self._row("JOES RESTAURANT"))
        assert p is not None
        assert p.category == "meals"

    def test_hotel_keyword(self):
        p = check_keywords(self._row("GRAND HOTEL"))
        assert p is not None
        assert p.category == "travel"

    def test_insurance_keyword(self):
        p = check_keywords(self._row("GEICO INSURANCE PREMIUM"))
        assert p is not None
        assert p.category == "insurance"


# ═══════════════════════════════════════════════════════════════════════════
# Stage 5: Refunds
# ═══════════════════════════════════════════════════════════════════════════

class TestRefunds:
    def test_refund_keyword_match(self):
        rows = [
            NormalizedRow(0, date(2026, 1, 1), "UBER TRIP", "UBER", -1840, "USD"),
            NormalizedRow(1, date(2026, 1, 15), "UBER REFUND", "UBER", 1840, "USD"),
        ]
        p = check_refund(rows[1], rows, {})
        assert p is not None
        assert p.category == "refund_reimbursement"

    def test_income_keyword(self):
        row = NormalizedRow(0, date(2026, 1, 1), "STRIPE PAYOUT", "STRIPE PAYOUT", 320000, "USD")
        p = check_refund(row, [row], {})
        assert p is not None
        assert p.category == "business_income"


# ═══════════════════════════════════════════════════════════════════════════
# Stage 6: Scoring
# ═══════════════════════════════════════════════════════════════════════════

class TestScoring:
    def test_determine_status_auto(self):
        assert determine_status(0.95) == "auto"

    def test_determine_status_suggested(self):
        assert determine_status(0.70) == "suggested"

    def test_determine_status_needs_review(self):
        assert determine_status(0.30) == "needs_review"


# ═══════════════════════════════════════════════════════════════════════════
# End-to-end pipeline
# ═══════════════════════════════════════════════════════════════════════════

class TestPipeline:
    def _make_rows(self) -> list[NormalizedRow]:
        return [
            NormalizedRow(0, date(2026, 1, 4), "ADOBE CREATIVE CLOUD",
                          "ADOBE CREATIVE CLOUD", -5999, "USD"),
            NormalizedRow(1, date(2026, 1, 5), "PAYMENT THANK YOU",
                          "PAYMENT THANK YOU", 150000, "USD"),
            NormalizedRow(2, date(2026, 1, 7), "JOES CAFE",
                          "JOES CAFE", -1420, "USD"),
            NormalizedRow(3, date(2026, 1, 9), "AMAZON",
                          "AMAZON", -13107, "USD"),
            NormalizedRow(4, date(2026, 1, 10), "GOOGLE ADS",
                          "GOOGLE ADS", -25000, "USD"),
            NormalizedRow(5, date(2026, 1, 14), "STRIPE PAYOUT",
                          "STRIPE PAYOUT", 320000, "USD"),
            NormalizedRow(6, date(2026, 1, 15), "TRANSFER TO CHECKING",
                          "TRANSFER TO CHECKING", -50000, "USD"),
        ]

    def test_pipeline_runs(self):
        rows = self._make_rows()
        results = run_pipeline(rows)
        assert len(results) == len(rows)

    def test_adobe_is_software(self):
        rows = self._make_rows()
        results = run_pipeline(rows)
        adobe = results[0]
        assert adobe.category == "software_subscriptions"
        assert adobe.status == "auto"

    def test_payment_is_excluded(self):
        rows = self._make_rows()
        results = run_pipeline(rows)
        payment = results[1]
        assert payment.category == "credit_card_payment"

    def test_transfer_is_excluded(self):
        rows = self._make_rows()
        results = run_pipeline(rows)
        transfer = results[6]
        assert transfer.category == "transfer"

    def test_google_ads_is_advertising(self):
        rows = self._make_rows()
        results = run_pipeline(rows)
        gads = results[4]
        assert gads.category == "advertising"

    def test_amazon_is_mixed_use(self):
        rows = self._make_rows()
        results = run_pipeline(rows)
        amzn = results[3]
        assert amzn.confidence <= 0.50
        assert "mixed_use_merchant" in amzn.flags

    def test_stripe_payout_is_income(self):
        rows = self._make_rows()
        results = run_pipeline(rows)
        stripe = results[5]
        assert stripe.category == "business_income"

    def test_user_rule_overrides(self):
        rows = [
            NormalizedRow(0, date(2026, 1, 7), "JOES CAFE",
                          "JOES CAFE", -1420, "USD"),
        ]
        rules = [
            UserRuleSpec(
                id=1,
                match_type="exact",
                pattern="JOES CAFE",
                category="meals",
            ),
        ]
        results = run_pipeline(rows, rules)
        assert results[0].category == "meals"
        assert results[0].confidence >= 0.98
        assert results[0].rule_id == 1

    def test_every_result_has_reason(self):
        rows = self._make_rows()
        results = run_pipeline(rows)
        for r in results:
            assert r.reason, f"Row {r.row_index} has no reason"

    def test_categories_exist(self):
        """Every result category should be in the master registry."""
        rows = self._make_rows()
        results = run_pipeline(rows)
        for r in results:
            assert r.category in CATEGORIES, f"Unknown category: {r.category}"
