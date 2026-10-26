"""Tests for the brain: rules, confidence bands and honest uncertainty.

Every case here mirrors an edge case from DESIGN.md - when you add a rule,
add the test next to it.
"""

import pytest

from app.brain.engine import categorize_statement
from app.brain.normalizer import normalize
from app.models import ParsedTransaction


def make(desc: str, amount: float, date: str = "2026-03-05"):
    return ParsedTransaction(date_raw=date, date=date, description=desc, amount=amount)


def cat_one(desc, amount):
    return categorize_statement([make(desc, amount)])[0][0]


# --- core categorization ---------------------------------------------------


def test_known_software_is_high_confidence():
    r = cat_one("ADOBE CREATIVE CLOUD", -54.99)
    assert r.category == "Software & Subscriptions"
    assert r.band == "high" and not r.needs_review


def test_unknown_merchant_goes_to_review():
    r = cat_one("JOES CAFE 9921", -4.50)
    assert r.category is None
    assert r.needs_review and r.band == "low"


def test_uber_trip_is_travel():
    r = cat_one("UBER *TRIP HELP.UBER.COM", -18.45)
    assert r.category == "Travel" and r.band == "high"


def test_uber_eats_is_meals_not_travel():
    r = cat_one("UBER EATS RESTAURANT", -23.90)
    assert r.category == "Meals & Coffee"


def test_generic_words_stay_low_confidence():
    r = cat_one("MAIN STREET DELI", -11.30)
    assert r.category is None and r.needs_review


def test_personal_subscription_flagged_as_personal():
    r = cat_one("NETFLIX.COM", -15.49)
    assert r.category == "Personal & Non-Business"


def test_ambiguous_amazon_needs_confirmation():
    # "amazon" alone is a weak 0.5 signal -> medium band -> user must confirm
    r = cat_one("AMAZON MKTPLACE PMTS", -38.72)
    assert r.category == "Office & Equipment"
    assert r.band == "medium" and r.needs_review


# --- special flows ----------------------------------------------------------


def test_transfer_to_savings_is_not_spending():
    r = cat_one("TRANSFER TO SAVINGS *OPEN", -500.00)
    assert r.category == "Transfers & Payments"
    assert not r.is_spending and not r.needs_review


def test_credit_card_payment_is_transfer():
    r = cat_one("CREDIT CARD PAYMENT THANK YOU", -750.00)
    assert r.category == "Transfers & Payments"


def test_stripe_payout_is_income():
    r = cat_one("STRIPE PAYOUT INV-1042", 1450.00)
    assert r.category == "Income" and not r.is_spending


def test_explicit_refund_links_to_original_category():
    r = cat_one("REFUND - STARBUCKS STORE 8842", 6.75)
    assert r.category == "Refunds"
    assert r.linked_category == "Meals & Coffee"
    assert not r.is_spending


def test_refund_links_on_weak_merchant_match():
    # the word "refund" anchors the decision, so a 0.5-weight merchant
    # (amazon) is enough to link it back to the original spend category
    r = cat_one("REFUND AMAZON MKTPLACE PMTS", 96.14)
    assert r.category == "Refunds"
    assert r.linked_category == "Office & Equipment"


def test_credit_from_known_merchant_treated_as_refund():
    r = cat_one("DELTA AIR LINES", 50.00)  # credit from an expense merchant
    assert r.category == "Refunds" and r.linked_category == "Travel"


def test_unexpected_credit_goes_to_review():
    # cannot tell income from refund -> ask, never guess
    r = cat_one("CHECK DEPOSIT 5500", 320.00)
    assert r.category is None and r.needs_review


# --- messy data --------------------------------------------------------------


def test_unreadable_date_goes_to_review():
    t = ParsedTransaction(date_raw="05/99/2026", date=None,
                          description="STARBUCKS", amount=-6.75,
                          issues=["unreadable date"])
    (rows, _) = categorize_statement([t])
    assert rows[0].category is None and rows[0].needs_review


def test_missing_amount_goes_to_review():
    t = ParsedTransaction(date_raw="2026-03-05", date="2026-03-05",
                          description="STARBUCKS", amount=0.0,
                          issues=["missing amount"])
    (rows, _) = categorize_statement([t])
    assert rows[0].needs_review


def test_duplicate_rows_are_flagged_not_merged():
    rows, _ = categorize_statement(
        [make("UBER *TRIP", -18.45), make("UBER *TRIP", -18.45)])
    assert "possible_duplicate" not in rows[0].flags
    assert "possible_duplicate" in rows[1].flags
    assert rows[1].needs_review


def test_ids_are_sequential():
    rows, _ = categorize_statement([make("FIGMA", -15.0), make("SLACK", -8.0)])
    assert [r.id for r in rows] == [1, 2]


# --- summary math ------------------------------------------------------------


def test_summary_buckets_and_exclusions():
    rows, summary = categorize_statement([
        make("ADOBE CREATIVE CLOUD", -54.99),
        make("FIGMA MONTHLY", -15.00),
        make("STRIPE PAYOUT INV-1", 1450.00),
        make("TRANSFER TO SAVINGS", -500.00),
        make("REFUND - STARBUCKS", 6.75),
        make("JOES CAFE 9921", -4.50),  # needs review, no category
    ])
    assert summary.spending_total == pytest.approx(69.99)
    assert summary.by_category["Software & Subscriptions"] == pytest.approx(69.99)
    assert summary.income_total == pytest.approx(1450.00)
    assert summary.transfers_total == pytest.approx(500.00)
    assert summary.refunds_total == pytest.approx(6.75)
    assert summary.review_count == 1
    assert summary.count == 6


def test_normalization_visible_in_output():
    r = cat_one("SQ *JOES CAFE, 9921", -4.50)
    assert r.normalized == normalize("SQ *JOES CAFE, 9921")
