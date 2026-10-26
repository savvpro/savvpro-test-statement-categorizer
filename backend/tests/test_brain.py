"""
Unit tests for the Brain decision engine and IRS Schedule C classification.
"""

from app.brain.categorizer import categorize_transaction
from app.brain.taxonomy import Category


def test_software_saas_matching():
    res1 = categorize_transaction("ADOBE *CREATIVE CLOUD 800-833-6687 CA", -54.99)
    assert res1.category == Category.SOFTWARE_SAAS
    assert res1.confidence >= 0.90
    assert res1.deductibility_pct == 1.0

    res2 = categorize_transaction("FIGMA INC INTERNET 415-555-0192 CA", -15.00)
    assert res2.category == Category.SOFTWARE_SAAS
    assert res2.confidence >= 0.90

    res3 = categorize_transaction("AWS WEB SERVICES CLOUD US-EAST", -184.20)
    assert res3.category == Category.SOFTWARE_SAAS
    assert res3.confidence >= 0.90


def test_travel_transit_matching():
    res1 = categorize_transaction("UBER *TRIP 10/14 SAN FRANCISCO CA", -28.40)
    assert res1.category == Category.TRAVEL_TRANSIT
    assert res1.confidence >= 0.90
    assert res1.deductibility_pct == 1.0

    res2 = categorize_transaction("DELTA AIR 00628392182 CONFERENCES", -420.00)
    assert res2.category == Category.TRAVEL_TRANSIT

    res3 = categorize_transaction("AIRBNB *HM918231 CHICAGO IL", -310.00)
    assert res3.category == Category.TRAVEL_TRANSIT


def test_equipment_hardware_safe_harbor():
    res = categorize_transaction("APPLE STORE #R102 5TH AVE NYC", -1299.00)
    assert res.category == Category.EQUIPMENT_HARDWARE
    assert res.confidence >= 0.90
    assert res.deductibility_pct == 1.0


def test_known_meal_chain_fifty_percent_rule():
    res = categorize_transaction("STARBUCKS STORE 08412 NEW YORK NY", -6.85)
    assert res.category == Category.BUSINESS_MEALS
    assert res.deductibility_pct == 0.50  # Statutory 50% IRS limit
    assert res.confidence >= 0.85


def test_ambiguous_local_cafe_goes_to_needs_review():
    # Prompt explicit rule: JOES CAFE 9921 is unknown, so it goes to Needs Review.
    res = categorize_transaction("JOES CAFE 9921 BROOKLYN NY", -14.75)
    assert res.category == Category.NEEDS_REVIEW
    assert res.needs_review is True
    assert res.suggested_category == Category.BUSINESS_MEALS
    assert "business client purpose" in res.reason.lower() or "cafe" in res.reason.lower()


def test_ambiguous_department_store():
    # Target / Walmart mixed personal and business
    res1 = categorize_transaction("TARGET T-0914 SAN FRANCISCO CA", -88.42)
    assert res1.category == Category.NEEDS_REVIEW
    assert res1.needs_review is True

    res2 = categorize_transaction("WALMART SUPERCENTER #1829", -134.18)
    assert res2.category == Category.NEEDS_REVIEW
    assert res2.needs_review is True


def test_fuzzy_matching_typo():
    # Statement typo: "ADOB CREATV CLD" should fuzzy match to Adobe
    res = categorize_transaction("ADOB CREATV CLD 800-833", -54.99)
    assert res.category == Category.SOFTWARE_SAAS
    assert "fuzzy" in res.reason.lower() or "adobe" in res.reason.lower()


def test_user_custom_rule_override():
    # If user maps JOES CAFE to Meals, it should apply with 1.0 confidence
    custom_rules = {"JOES CAFE": Category.BUSINESS_MEALS}
    res = categorize_transaction("JOES CAFE 9921 BROOKLYN NY", -14.75, user_rules=custom_rules)
    assert res.category == Category.BUSINESS_MEALS
    assert res.confidence == 1.0
    assert "user custom rule" in res.reason.lower()
