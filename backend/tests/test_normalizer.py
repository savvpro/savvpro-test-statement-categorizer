import pytest

from app.engine.normalizer import normalize


@pytest.mark.parametrize(
    ("raw", "merchant"),
    [
        ("SQ *JOES CAFE 9921", "JOES CAFE"),
        ("JOES CAFE 9921", "JOES CAFE"),
        ("PAYPAL *ADOBE", "ADOBE"),
        ("TST* BLUE BOTTLE COFFEE", "BLUE BOTTLE COFFEE"),
        ("UBER *TRIP 8812", "UBER TRIP"),
        ("AMAZON.COM*2K4L1", "AMAZON COM"),
        ("STAPLES 00231", "STAPLES"),
        ("  adobe   creative cloud ", "ADOBE CREATIVE CLOUD"),
        ("T-MOBILE", "T MOBILE"),
        ("AT&T WIRELESS", "AT&T WIRELESS"),
        ("MICROSOFT 365", "MICROSOFT 365"),  # short numbers that are part of a name stay
        ("POS SQ *JOES CAFE", "JOES CAFE"),  # stacked prefixes
        ("STORE #1234 ROMA", "STORE ROMA"),
    ],
)
def test_normalize_merchant(raw, merchant):
    assert normalize(raw).merchant == merchant


def test_foreign_currency_is_extracted():
    result = normalize("HOTEL LISBOA EUR 120.00")
    assert result.merchant == "HOTEL LISBOA"
    assert result.foreign_currency == "EUR"
    assert result.foreign_amount == 120.0


def test_foreign_amount_with_thousands_separator():
    result = normalize("TOKYO INN JPY 12,500.00")
    assert (result.foreign_currency, result.foreign_amount) == ("JPY", 12500.0)


def test_only_a_prefix_is_kept_rather_than_emptied():
    assert normalize("SQ *").merchant == "SQ"


def test_reference_only_description_falls_back_to_text():
    assert normalize("123456").merchant == "123456"
