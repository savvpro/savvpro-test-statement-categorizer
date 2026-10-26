from decimal import Decimal as D

import pytest

from app.brain.classifier import classify
from app.brain.normalizer import normalize


def test_normalize_strips_codes_and_spaces():
    assert normalize("UBER *TRIP 8821") == "UBER TRIP"
    assert normalize("  joes   cafe 9921 ") == "JOES CAFE"


@pytest.mark.parametrize("desc,amount,expected", [
    ("ADOBE CREATIVE CLOUD", "-54.99", "Software"),
    ("UBER *TRIP 8821", "-23.40", "Travel"),
    ("UBER EATS 123", "-18.00", "Meals"),
    ("TRANSFER TO SAVINGS", "-500.00", "Transfer"),
    ("CLIENT PAYMENT ACME", "1500.00", "Income"),
    ("AMAZON REFUND", "29.99", "Refund"),
    ("AMAZON MARKETPLACE", "-45.00", "Needs Review"),
    ("AMAZON WEB SERVICES", "-12.00", "Software"),
    ("JOES CAFE 9921", "-12.50", "Needs Review"),
    ("", "-5.00", "Needs Review"),
])
def test_classify(desc, amount, expected):
    assert classify(desc, D(amount)).category == expected


@pytest.mark.parametrize("desc,amount,expected", [
    ("adobe creative cloud", "-5.00", "Software"),
    ("ZOOM.US 888123", "-15.99", "Software"),
    ("QANTAS AIRWAYS", "-320.00", "Travel"),
    ("WOOLWORTHS 1234", "-85.00", "Needs Review"),
    ("ADOBE REFUND", "54.99", "Refund"),
    ("ADOBE", "54.99", "Needs Review"),
    ("TRANSFER FROM SAVINGS", "500.00", "Transfer"),
    ("CLIENT PAYMENT ACME", "0", "Needs Review"),
    ("SOME STORE RETURN", "20.00", "Refund"),
    ("   ###   ", "-9.00", "Needs Review"),
])
def test_classify_edge_cases(desc, amount, expected):
    assert classify(desc, D(amount)).category == expected