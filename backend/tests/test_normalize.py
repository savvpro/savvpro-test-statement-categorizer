import pytest

from app.ingest.normalize import clean, merchant_key


@pytest.mark.parametrize(
    "raw,key",
    [
        ("SQ *JOES CAFE #9921 DALLAS TX", "JOES CAFE"),
        ("JOES CAFE 0412", "JOES CAFE"),
        ("POS PURCHASE BUC-EES #22 FRISCO TX", "BUC-EES FRISCO"),
        ("AUTOZONE #4410 REFUND", "AUTOZONE"),
        ("SPOTHERO 7Y2K", "SPOTHERO 7Y2K"),  # "SP" prefix needs its asterisk
    ],
)
def test_merchant_key(raw, key):
    assert merchant_key(raw) == key


def test_clean_removes_masked_card_and_dates():
    assert clean("CHECKCARD 0914 SHELL OIL XXXX1234 09/14") == "SHELL OIL"
