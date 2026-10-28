import pytest

from app.normalize.merchant import clean_description, is_person_like


@pytest.mark.parametrize(
    ("raw", "key", "channel", "counterparty"),
    [
        ("SQ *JOES CAFE 9921 SEATTLE WA", "JOES CAFE", "CARD", None),
        (
            "ZELLE FROM MARIA K LOPEZ CONF# 88H2",
            "ZELLE MARIA K LOPEZ",
            "ZELLE",
            "MARIA K LOPEZ",
        ),
        ("POS DEBIT HOME DEPOT #4410 TACOMA WA", "HOME DEPOT", "CARD", None),
        ("AMZN MKTP US*2K4T81", "AMAZON", "CARD", None),
        ("CHECK #1042", "CHECK", "CHECK", None),
    ],
)
def test_spec_example_table(raw: str, key: str, channel: str, counterparty: str | None) -> None:
    assert clean_description(raw) == (key, channel, counterparty)


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("THE HOME DEPOT #123", "HOME DEPOT"),
        ("WM SUPERCENTER #2114 TACOMA WA", "WALMART"),
        ("LOWE'S #1234 PORTLAND OR", "LOWES"),
        ("PAYPAL *NETFLIX 4029357733 CA", "NETFLIX"),
        ("STATE FARM INSURANCE WA", "STATE FARM INSURANCE"),
        ("HOME DEPOT WA", "HOME DEPOT"),
        ("TST* BURGER PLACE 12/05", "BURGER PLACE"),
        ("CHECKCARD 0105 SHELL OIL 57444 SEATTLE WA", "SHELL OIL"),
        ("PURCHASE AUTHORIZED ON 01/05 CHEVRON GAS 0098 TACOMA WA", "CHEVRON GAS"),
        ("DEBIT CARD PURCHASE COSTCO WHSE #123", "COSTCO WHSE"),
        ("AMAZON.COM*AB12CD34 AMZN.COM/BILL WA", "AMAZON"),
        ("COMCAST 800-555-1212 WA", "COMCAST"),
        ("XXXXXX1234 PUGET SOUND ENERGY", "PUGET SOUND ENERGY"),
        ("Café du Monde", "CAFE DU MONDE"),
        ("   ", "UNKNOWN"),
        ("#### 12345", "UNKNOWN"),
        ("ACH DEBIT STATE FARM REF 99887766", "STATE FARM"),
        ("DIRECT DEPOSIT ACME PAYROLL", "ACME PAYROLL"),
        ("WIRE IN ACME HOLDINGS", "ACME HOLDINGS"),
        ("VENMO PAYMENT FROM JOHN DOE ID 12345", "VENMO JOHN DOE"),
        ("CASH APP PAYMENT FROM JANE ROE", "CASH APP JANE ROE"),
        ("ZELLE TO BOB BUILDER REF 123", "ZELLE BOB BUILDER"),
    ],
)
def test_more_cleaning_cases(raw: str, key: str) -> None:
    assert clean_description(raw)[0] == key


def test_channels() -> None:
    assert clean_description("ACH DEBIT FOO")[1] == "ACH"
    assert clean_description("WIRE OUT BAR")[1] == "WIRE"
    assert clean_description("VENMO PAYMENT FROM JOHN DOE")[1] == "VENMO"
    assert clean_description("PLAIN MERCHANT")[1] is None


def test_key_is_idempotent_and_capped() -> None:
    for raw in ["SQ *JOES CAFE 9921 SEATTLE WA", "ZELLE FROM A B CONF 1", "X" * 500, "A B C TX WA"]:
        key = clean_description(raw)[0]
        assert clean_description(key)[0] == key
        assert 0 < len(key) <= 128


def test_person_like() -> None:
    assert is_person_like("MARIA K LOPEZ")
    assert is_person_like("BOB SMITH")
    assert not is_person_like("SMITH PLUMBING")
    assert not is_person_like("ACME")
    assert not is_person_like("A B C D")
    assert not is_person_like("BOB SMITH LLC")


def test_long_pathological_input_is_fast() -> None:
    clean_description("ZELLE FROM " + "A " * 5000 + "CONF")
    clean_description("ID " * 5000)
