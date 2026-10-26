"""
Unit tests for merchant description cleaning and sanitization.
"""

import pytest
from app.brain.sanitizer import sanitize_merchant


def test_sanitize_github_with_pos_and_location():
    raw = "CHECKCARD POS PURCHASE SQ *GITHUB #1042 SAN FRANCISCO CA"
    result = sanitize_merchant(raw)
    assert result == "GITHUB"


def test_sanitize_starbucks_store():
    raw = "TST*STARBUCKS STORE 18294 SEATTLE WA"
    result = sanitize_merchant(raw)
    assert "STARBUCKS" in result


def test_sanitize_amazon_abbreviation():
    raw = "AMZN Mktp US* 2B71X99 AMAZON.COM WA"
    result = sanitize_merchant(raw)
    assert "AMAZON" in result


def test_sanitize_apple():
    raw = "APL* APPLE.COM/BILL 800-275-2273 CA"
    result = sanitize_merchant(raw)
    assert "APPLE" in result


def test_sanitize_uber_trip():
    raw = "UBER *TRIP HELP.UBER.COM"
    result = sanitize_merchant(raw)
    assert "UBER" in result


def test_sanitize_airline_with_ticket_number():
    raw = "DELTA AIR 0062839201842"
    result = sanitize_merchant(raw)
    assert result == "DELTA AIR"


def test_sanitize_recurring_transaction():
    raw = "RECURRING TRANSACTION GITHUB INC"
    result = sanitize_merchant(raw)
    assert "GITHUB" in result


def test_sanitize_empty_and_whitespace():
    assert sanitize_merchant("") == "UNKNOWN"
    assert sanitize_merchant("   ") == "UNKNOWN"
    assert sanitize_merchant(None) == "UNKNOWN"


def test_sanitize_short_fallback():
    assert sanitize_merchant("X") == "X"
    assert sanitize_merchant("A") == "A"


def test_sanitize_preserves_clean_vendor():
    assert sanitize_merchant("VERCEL") == "VERCEL"
    assert sanitize_merchant("MICRO CENTER") == "MICRO CENTER"
