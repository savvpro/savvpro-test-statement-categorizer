from decimal import Decimal

import pytest

from app.categorizer import categorize, normalize

OUT = Decimal("-20.00")  # a charge
IN = Decimal("20.00")  # money back


@pytest.mark.parametrize("text,expected", [
    ("ADOBE CREATIVE CLOUD", "Software"),
    ("UBER *TRIP 8821", "Travel"),
    ("UBER EATS 5521", "Meals"),          # longer keyword beats "UBER"
    ("aws emea", "Software"),
    ("Staples Store 4412", "Office Supplies"),
    ("GOOGLE ADS 7765", "Advertising"),
    ("PTCL BROADBAND", "Utilities"),
])
def test_known_merchants(text, expected):
    result = categorize(text, OUT)
    assert result.category == expected
    assert result.status == "ok"


def test_unknown_merchant_needs_review():
    result = categorize("XYZ CONSULTING LTD", OUT)
    assert result.category == "Needs Review"
    assert result.status == "needs_review"


def test_cafe_word_is_meals():
    assert categorize("JOES CAFE 9921", OUT).category == "Meals"


def test_ambiguous_merchant_needs_review():
    assert categorize("AMAZON MKTPLACE 1123", OUT).category == "Needs Review"


def test_specific_beats_ambiguous():
    assert categorize("AMAZON WEB SERVICES", OUT).category == "Software"


def test_whole_word_matching():
    # "AWS" must not match inside "LAWS"
    assert categorize("LAWS OF DESIGN", OUT).category == "Needs Review"


def test_transfer_is_not_spending():
    assert categorize("TRANSFER TO SAVINGS", OUT).category == "Not Spending"
    assert categorize("PAYMENT THANK YOU", IN).category == "Not Spending"


def test_refund_is_not_income():
    result = categorize("REFUND ADOBE CREATIVE CLOUD", IN)
    assert result.category == "Refund"
    assert result.refund_of == "Software"


def test_credit_from_known_merchant_is_refund():
    result = categorize("FIGMA PROFESSIONAL", IN)
    assert (result.category, result.refund_of) == ("Refund", "Software")


def test_unknown_credit_needs_review():
    assert categorize("XYZ CONSULTING LTD", IN).category == "Needs Review"


def test_refund_word_on_a_charge_needs_review():
    assert categorize("REFUND PROCESSING FEE", OUT).category == "Needs Review"


def test_empty_description_needs_review():
    assert categorize("   ", OUT).category == "Needs Review"


def test_normalize_removes_noise():
    assert normalize("Uber *Trip 8821") == "UBER TRIP"
    assert normalize("JOES CAFE   #9921") == "JOES CAFE"
