from app.services.categorizer import categorize
from app.models.transaction import Category


def test_software():
    cat, conf = categorize("ADOBE CREATIVE CLOUD", 54.99)
    assert cat == Category.SOFTWARE
    assert conf == "high"

def test_travel():
    cat, conf = categorize("UBER *TRIP", 12.50)
    assert cat == Category.TRAVEL

def test_meals():
    cat, conf = categorize("STARBUCKS COFFEE", 5.80)
    assert cat == Category.MEALS

def test_transfer():
    cat, conf = categorize("TRANSFER TO SAVINGS", 500.00)
    assert cat == Category.TRANSFER

def test_refund():
    cat, conf = categorize("ADOBE REFUND", -54.99)
    assert cat == Category.REFUND

def test_needs_review():
    cat, conf = categorize("UNKNOWN MERCHANT XYZ 9921", 45.00)
    assert cat == Category.NEEDS_REVIEW