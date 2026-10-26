"""Unit tests for transaction description normalization.

Verifies deterministic behavior, whitespace collapsing, case normalization,
empty string handling, and preservation of merchant identifiers and punctuation.
"""

import pytest
from app.services.transaction_normalizer import normalize_description


def test_leading_and_trailing_whitespace():
    """Verify leading and trailing spaces, tabs, and newlines are stripped."""
    assert normalize_description("  GITHUB INC   ") == "GITHUB INC"
    assert normalize_description("\tAWS BILLING\n") == "AWS BILLING"
    assert normalize_description("   \t  ") == ""


def test_repeated_whitespace_collapsing():
    """Verify multiple spaces and mixed whitespace inside text collapse to single space."""
    assert normalize_description("DIGITALOCEAN   VPS     CLOUD") == "DIGITALOCEAN VPS CLOUD"
    assert normalize_description("CLIENT\t\tPAYMENT\n\nACME") == "CLIENT PAYMENT ACME"


def test_case_normalization():
    """Verify lowercase and mixed-case descriptions normalize to consistent uppercase."""
    assert normalize_description("github copilot") == "GITHUB COPILOT"
    assert normalize_description("GitHub CoPiLoT") == "GITHUB COPILOT"
    assert normalize_description("uber *trip") == "UBER *TRIP"


def test_empty_and_none_descriptions():
    """Verify empty string, whitespace-only, and None produce an empty string safely."""
    assert normalize_description("") == ""
    assert normalize_description("     ") == ""
    assert normalize_description(None) == ""


def test_punctuation_preservation():
    """Ensure non-destructive normalization preserves symbols like *, ., #, -, and @."""
    assert normalize_description("UBER *TRIP 1234") == "UBER *TRIP 1234"
    assert normalize_description("AMAZON.COM*MEMBER") == "AMAZON.COM*MEMBER"
    assert normalize_description("INVOICE #1024-A") == "INVOICE #1024-A"
    assert normalize_description("CURSOR.SH") == "CURSOR.SH"
    assert normalize_description("AT&T BILL PAYMENT") == "AT&T BILL PAYMENT"


def test_deterministic_normalization():
    """Ensure identical inputs always produce the exact same normalized output across calls."""
    raw = "   DIGITALOCEAN.COM\t\tSERVER #42   "
    result1 = normalize_description(raw)
    result2 = normalize_description(raw)
    result3 = normalize_description(raw)

    assert result1 == result2 == result3 == "DIGITALOCEAN.COM SERVER #42"
