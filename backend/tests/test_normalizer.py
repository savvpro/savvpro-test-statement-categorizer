import pytest
from app.engine.normalizer import MerchantNormalizer


def test_strip_square_prefix():
    display, key = MerchantNormalizer.clean("SQ *JOES CAFE 9921 SAN FRANCISCO CA")
    assert "Square" not in display
    assert "9921" not in display
    assert "Joe's Cafe" in display or "Joes Cafe" in display


def test_strip_toast_prefix():
    display, key = MerchantNormalizer.clean("TST* BLUE BOTTLE COFFEE #12")
    assert "TST" not in display
    assert "#12" not in display
    assert "Blue Bottle" in display


def test_strip_paypal_and_phone():
    display, key = MerchantNormalizer.clean("PAYPAL *GITHUB INC 402-935-7733 CA")
    assert "PAYPAL" not in display
    assert "402-935-7733" not in display
    assert display == "GitHub"


def test_strip_amazon_marketplace():
    display, key = MerchantNormalizer.clean("AMZN Mktp US*2J9K10931 Amzn.com/bill WA")
    assert "Mktp" not in display
    assert "WA" not in display
    assert "Amzn" in display or "Amazon" in display


def test_known_aliases():
    display, _ = MerchantNormalizer.clean("ADOBE *CREATIVE CLOUD 800-833-6687 CA")
    assert display == "Adobe Creative Cloud"

    display2, _ = MerchantNormalizer.clean("UBER *TRIP HELP.UBER.COM")
    assert display2 == "Uber"
