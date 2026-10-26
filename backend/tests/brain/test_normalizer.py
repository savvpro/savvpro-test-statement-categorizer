import pytest

from app.brain.normalizer import merchant_key


@pytest.mark.parametrize(
    ("description", "key"),
    [
        ("adobe   creative cloud", "ADOBE CREATIVE CLOUD"),
        ("SQ *JOES CAFE 9921", "JOES CAFE"),
        ("TST* BLUE FIG BISTRO", "BLUE FIG BISTRO"),
        ("TST*BLUE FIG BISTRO", "BLUE FIG BISTRO"),
        ("PAYPAL *FIVERR 4029357733", "FIVERR"),
        ("PP*ETSY 01/15", "ETSY"),
        ("GOOGLE *WORKSPACE SAMRIV", "WORKSPACE SAMRIV"),
        ("POS SQ *MARLOW BAKERY", "MARLOW BAKERY"),
        ("PURCHASE AUTHORIZED ON 01/05 SQ *JOES CAFE", "JOES CAFE"),
        ("TRADER JOES #552", "TRADER JOES"),
        ("BEST BUY 00123", "BEST BUY"),
        ("ONLINE TRANSFER TO SAVINGS XXXX5521", "ONLINE TRANSFER TO SAVINGS"),
        ("CARD ENDING ****4421 FAKE STORE", "CARD ENDING FAKE STORE"),
        ("XFINITY INTERNET 800-555-0142", "XFINITY INTERNET"),
        ("FAKE PLUMBING (512) 555-0199", "FAKE PLUMBING"),
        ("STRIPE TRANSFER ST-8F3K2L9Q", "STRIPE TRANSFER"),
        ("ACH DEPOSIT HARBOR & PINE CO INV-2026-001", "ACH DEPOSIT HARBOR & PINE CO"),
        ("NETFLIX.COM", "NETFLIX"),
        ("UBER *TRIP HELP.UBER.COM", "UBER TRIP"),
        ("AWS EMEA AWS.AMAZON.CO", "AWS EMEA"),
        ("MARRIOTT AUSTIN TX", "MARRIOTT"),
        ("JOES CAFE SAN FRANCISCO CA", "JOES CAFE"),
        ("HARBOR & PINE CO", "HARBOR & PINE CO"),  # CO is not treated as Colorado
        ("DELTA AIR LINES 0062391", "DELTA AIR LINES"),
        ("3M STORE", "3M STORE"),  # short alphanumerics are part of the name
    ],
)
def test_merchant_key(description: str, key: str) -> None:
    assert merchant_key(description) == key


def test_never_empty() -> None:
    assert merchant_key("#1234") == "#1234"
    assert merchant_key("  12345  ") == "12345"


def test_same_merchant_same_key() -> None:
    a = merchant_key("SQ *JOES CAFE 9921 01/09")
    b = merchant_key("SQ * JOES CAFE #9921")
    assert a == b == "JOES CAFE"
