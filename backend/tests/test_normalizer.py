from app.normalizer import has_usd, normalize


def test_strips_star_and_order_number():
    assert normalize("FOODPANDA*ORDER 4471920") == "FOODPANDA ORDER"


def test_strips_masked_account_digits():
    assert normalize("IBFT TO SAVINGS A/C 0042****7781") == "IBFT TO SAVINGS A/C"
    assert normalize("RAAST P2P TO ALI RAZA 0333****918") == "RAAST P2P TO ALI RAZA"


def test_strips_alphanumeric_order_id_and_keeps_usd_as_feature():
    raw = "AMZN MKTP US*2K4LP8 USD 34.99"
    assert normalize(raw) == "AMZN MKTP US"
    assert has_usd(raw)


def test_lowercase_and_double_spaces():
    assert normalize("payoneer inc funds trf ref 88954") == "PAYONEER INC FUNDS TRF REF"
    assert normalize("KFC  DHA RAYA 0112") == "KFC DHA RAYA"


def test_no_usd_hint_on_local_rows():
    assert not has_usd("LESCO ONLINE BILL PAY 1234567890")


def test_keeps_non_order_tokens():
    assert normalize("IMTIAZ SUPER MARKET DHA PH5") == "IMTIAZ SUPER MARKET DHA PH5"
