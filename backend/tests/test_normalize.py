import pytest

from app.brain.normalize import normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("POS PURCHASE SQ *JOES CAFE 9921 SAN JOSE CA", "JOES CAFE SAN JOSE"),
        (
            "PURCHASE AUTHORIZED ON 03/12 SQ *JOES CAFE #9921 SAN JOSE CA CARD 4417",
            "JOES CAFE SAN JOSE",
        ),
        ("UBER USA 6787 EDI PYMNTS PPD ID: 3450000000", "UBER USA EDI PYMNTS"),
        ("AMAZON.COM*2K4LM19QX AMZN.COM/BILL WA", "AMAZON.COM AMZN.COM/BILL"),
        ("TRANSFER TO SAVINGS XXXXXX1234", "TRANSFER TO SAVINGS"),
        ("T-MOBILE *AUTOPAY 800-937-8997 WA", "T-MOBILE AUTOPAY"),
        ("MOBILE DEPOSIT REF NUMBER 900000001", "MOBILE DEPOSIT"),
        ("  shell   oil 57444  ", "SHELL OIL"),
        ("GOOGLE *FI WRDN3B GOOGLE.COM CA", "GOOGLE FI GOOGLE.COM"),
    ],
)
def test_normalize_strips_bank_noise(raw, expected):
    assert normalize(raw).text == expected


def test_variants_share_a_key():
    a = normalize("POS PURCHASE SQ *JOES CAFE 9921 SAN JOSE CA")
    b = normalize("PURCHASE AUTHORIZED ON 03/12 SQ *JOES CAFE #9921 SAN JOSE CA CARD 4417")
    assert a.key == b.key == "joes cafe san jose"


def test_keeps_short_brand_numbers():
    assert normalize("PHILLIPS 66 #12345").text == "PHILLIPS 66"


def test_all_noise_falls_back_to_raw():
    assert normalize("123456").text == "123456"
