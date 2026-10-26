import pytest

from app.brain.normalizer import normalize


@pytest.mark.parametrize(
    ("raw", "text", "merchant_key"),
    [
        # processor prefixes are removed at the start
        ("SQ *JOES CAFE 9921 ISLAMABAD", "JOES CAFE 9921 ISLAMABAD", "JOES CAFE ISLAMABAD"),
        ("SQ*JOES CAFE", "JOES CAFE", "JOES CAFE"),
        ("sq * joes cafe", "JOES CAFE", "JOES CAFE"),
        ("PAYPAL *UPWORK 4029357733", "UPWORK 4029357733", "UPWORK"),
        ("TST*BLUE BIRD CAFE", "BLUE BIRD CAFE", "BLUE BIRD CAFE"),
        ("TST* BLUE BIRD CAFE", "BLUE BIRD CAFE", "BLUE BIRD CAFE"),
        ("POS PAPERWORLD STATIONERS F-10 ISB", "PAPERWORLD STATIONERS F-10 ISB",
         "PAPERWORLD STATIONERS ISB"),
        # Uber is the merchant, so its star is not a processor prefix
        ("UBER *TRIP HELP.UBER.COM", "UBER *TRIP HELP.UBER.COM", "UBER *TRIP HELP.UBER.COM"),
        ("UBER EATS LAHORE", "UBER EATS LAHORE", "UBER EATS LAHORE"),
        # prefixes only count at the start, and only as whole prefixes
        ("ADOBE SQ *THING", "ADOBE SQ *THING", "ADOBE SQ *THING"),
        ("POSTAL SERVICES KARACHI", "POSTAL SERVICES KARACHI", "POSTAL SERVICES KARACHI"),
        ("PAYPAL TRANSFER", "PAYPAL TRANSFER", "PAYPAL TRANSFER"),
        ("SQ *PAYPAL *X", "PAYPAL *X", "PAYPAL *X"),  # only one prefix is removed
        # whitespace and case
        ("  github inc   san francisco ca ", "GITHUB INC SAN FRANCISCO CA",
         "GITHUB INC SAN FRANCISCO CA"),
        ("UBER   *TRIP    HELP.UBER.COM", "UBER *TRIP HELP.UBER.COM", "UBER *TRIP HELP.UBER.COM"),
        ("a\tb c", "A B C", "A B C"),
        # tokens that contain a digit are dropped from the key only
        ("ZOOM.US 888-799-9666 CA", "ZOOM.US 888-799-9666 CA", "ZOOM.US CA"),
        ("CANVA* I04512-33871 SYDNEY AU", "CANVA* I04512-33871 SYDNEY AU", "CANVA* SYDNEY AU"),
        ("XYZ TRADERS 4471 RAWALPINDI", "XYZ TRADERS 4471 RAWALPINDI", "XYZ TRADERS RAWALPINDI"),
        ("ZONG 4G DEVICE RECHARGE", "ZONG 4G DEVICE RECHARGE", "ZONG DEVICE RECHARGE"),
        # degenerate input
        ("", "", ""),
        ("   ", "", ""),
        ("SQ *", "", ""),
        ("12345 6789", "12345 6789", ""),
    ],
)
def test_normalize(raw: str, text: str, merchant_key: str) -> None:
    result = normalize(raw)
    assert result.text == text
    assert result.merchant_key == merchant_key


def test_same_merchant_different_store_numbers_share_a_key() -> None:
    a = normalize("SQ *JOES CAFE 9921 ISLAMABAD")
    b = normalize("sq *joes  cafe 1002 islamabad")
    assert a.merchant_key == b.merchant_key
