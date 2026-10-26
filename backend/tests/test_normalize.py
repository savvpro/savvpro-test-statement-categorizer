import pytest

from app.brain.normalize import normalize


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("SQ *JOES CAFE 9921 SAN JOSE CA", "JOES CAFE SAN JOSE"),
        ("ADOBE *CREATIVE CLOUD 800-833-6687 CA", "ADOBE CREATIVE CLOUD"),
        ("AMZN MKTP US*2K4PX0RT1", "AMZN MKTP"),
        ("PAYPAL *JSMITHDESIGN", "JSMITHDESIGN"),
        ("STARBUCKS STORE 04412", "STARBUCKS STORE"),
        ("GOOGLE *ADS3847261", "GOOGLE ADS"),
        ("www.namecheap.com", "NAMECHEAP"),
        ("McDonald's #1234", "MCDONALDS"),
        ("CAFÉ DE FLORE", "CAFE DE FLORE"),
    ],
)
def test_merchant_key(raw, key):
    assert normalize(raw).key == key


def test_does_not_strip_prefix_letters_from_real_names():
    # "SP" and "PP" are processor prefixes, but only when followed by a separator.
    assert normalize("SPOTIFY USA").key == "SPOTIFY"
    assert normalize("PPG PAINTS").key == "PPG PAINTS"
    assert normalize("SQUARESPACE").key == "SQUARESPACE"


def test_same_merchant_different_store_numbers_share_a_key():
    assert normalize("STARBUCKS STORE 04412").key == normalize("STARBUCKS STORE 99120 NY").key


def test_phrase_tokens_keep_numbers():
    assert "365" in normalize("MICROSOFT 365 PERSONAL").all_tokens


def test_empty_and_symbol_only_descriptions_do_not_crash():
    assert normalize("").key == ""
    assert normalize("***").key == ""
    assert normalize("12345").key == "12345"
