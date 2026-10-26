"""Unit tests for merchant normalization."""
import pytest

from app.brain.normalize import normalize_merchant


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Processor prefix stripping
        ("SQ *JOES CAFE 9921 BROOKLYN NY", "JOES CAFE"),
        ("TST* THE GRID BISTRO SAN FRANCISCO CA", "THE GRID BISTRO SAN FRANCISCO"),  # state stripped; multi-word city kept

        ("PAYPAL *ADOBE CREATIVE CLOUD", "ADOBE CREATIVE CLOUD"),
        ("POS DEBIT STARBUCKS STORE 12345", "STARBUCKS STORE"),
        ("DEBIT CARD PURCHASE AMAZON MARKETPLACE", "AMAZON MARKETPLACE"),
        ("ACH DEBIT GITHUB INC", "GITHUB INC"),
        ("ACH CREDIT STRIPE TRANSFER", "STRIPE TRANSFER"),
        ("CHECKCARD 1234 UBER TRIP", "UBER TRIP"),
        # URL stripping
        ("UBER *TRIP HELP.UBER.COM CA", "UBER"),
        # Trailing state
        ("LYFT RIDE REQUEST CHICAGO IL", "LYFT RIDE REQUEST CHICAGO"),  # state stripped; city kept

        # Store number
        ("STARBUCKS #5091", "STARBUCKS"),
        # Phone number
        ("SOME VENDOR 555-867-5309", "SOME VENDOR"),
        # Already clean
        ("ADOBE CREATIVE CLOUD", "ADOBE CREATIVE CLOUD"),
        ("GOOGLE ADS", "GOOGLE ADS"),
        # Empty-ish inputs
        ("   FIGMA   ", "FIGMA"),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize_merchant(raw) == expected
