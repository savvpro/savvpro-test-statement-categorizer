# backend/tests/test_brain.py  (starter)
from decimal import Decimal
from datetime import date
from app.brain.engine import categorize
from app.brain.models import Transaction, Category

def _tx(desc, amt):
    return Transaction(date(2026, 10, 1), desc, Decimal(amt))

def test_refund_beats_merchant():
    d = categorize(_tx("AMAZON REFUND", "25.00"))
    assert d.category == Category.REFUND

def test_transfer_not_spending():
    d = categorize(_tx("TRANSFER TO SAVINGS", "-500.00"))
    assert d.category == Category.NOT_SPENDING

def test_shopify_payout_is_income():
    d = categorize(_tx("SHOPIFY PAYOUT 8821", "1200.00"))
    assert d.category == Category.INCOME

def test_known_merchant():
    d = categorize(_tx("USPS POSTAGE 4412", "-18.40"))
    assert d.category == Category.SHIPPING
    assert d.confidence >= 0.80

def test_unknown_goes_to_review():
    d = categorize(_tx("ZXCV TRADING 99", "-300.00"))
    assert d.category == Category.NEEDS_REVIEW