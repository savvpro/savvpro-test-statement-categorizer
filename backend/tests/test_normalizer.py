import pytest


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("FOODPANDA*ORDER 77812", "FOODPANDA ORDER"),
        ("SHELL PETROL STN #4421 LAHORE", "SHELL PETROL STN"),
        ("shell petrol stn #4421 lahore", "SHELL PETROL STN"),  # case
        ("  UBER   BV   PAYOUT  88213 ", "UBER BV PAYOUT"),  # whitespace and reference number
        ("POS 01/10 JAZZ MOBILE BILL", "JAZZ MOBILE BILL"),  # date and POS noise
        ("TXN12345 NETFLIX.COM", "NETFLIX COM"),  # mixed alphanumeric reference
        ("SHELL PETROL STN 9", "SHELL PETROL STN"),  # a bare branch number
        ("M2 MOTORWAY TOLL PLAZA", "M2 MOTORWAY TOLL PLAZA"),  # short numbers are real words
        ("ZONG 4G INTERNET", "ZONG 4G INTERNET"),
        ("E-TAG RECHARGE", "E TAG RECHARGE"),
        ("", ""),
        ("12345 / *** ###", ""),  # nothing left once the noise is gone
        ("كراچی ٹول 4412", "كراچی ٹول"),  # non-Latin scripts survive
    ],
)
def test_normalize(brain, raw, expected):
    assert brain.normalize(raw) == expected


def test_same_merchant_different_reference_gives_same_key(brain):
    assert brain.normalize("ALI TRADERS 5521") == brain.normalize("Ali Traders #7733")
