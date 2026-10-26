"""Tests for the normalizer (brain/normalizer.py)."""

from app.brain.normalizer import normalize


class TestNormalizer:
    def test_uppercase(self):
        assert normalize("starbucks coffee") == "STARBUCKS COFFEE"

    def test_strip_sq_prefix(self):
        assert normalize("SQ *Joes Cafe") == "JOES CAFE"

    def test_strip_paypal_prefix(self):
        assert normalize("PAYPAL *EBAY SELLER") == "EBAY SELLER"

    def test_strip_amzn_prefix(self):
        assert normalize("AMZN Mktp US*BOOKS") == "BOOKS"

    def test_strip_pos_prefix(self):
        assert normalize("POS PURCHASE STARBUCKS") == "STARBUCKS"

    def test_strip_trailing_store_number(self):
        assert normalize("STARBUCKS #1234") == "STARBUCKS"

    def test_collapse_whitespace(self):
        assert normalize("STARBUCKS    COFFEE   SHOP") == "STARBUCKS COFFEE SHOP"

    def test_empty_string(self):
        assert normalize("") == ""
        assert normalize("   ") == ""

    def test_none_input(self):
        assert normalize(None) == ""

    def test_no_prefix_no_change(self):
        assert normalize("ADOBE CREATIVE CLOUD") == "ADOBE CREATIVE CLOUD"
