from app.engine.normalizer import normalize_description


def test_strip_bank_prefixes():
    assert normalize_description("POS PURCHASE GITHUB INC") == "GITHUB INC"
    assert normalize_description("CHECKCARD 1024 UBER TRIP") == "UBER TRIP"
    assert normalize_description("DEBIT CARD TRANSACTION JETBRAINS") == "JETBRAINS"
    assert normalize_description("PURCHASE AUTHORIZED ON 10/12 APPLE.COM") == "APPLE.COM"
    assert normalize_description("DIRECT DEP - STRIPE PAYOUT") == "STRIPE PAYOUT"


def test_strip_aggregators():
    assert normalize_description("PAYPAL *HEROKU") == "HEROKU"
    assert normalize_description("SQ *BLUE BOTTLE COFFEE") == "BLUE BOTTLE COFFEE"
    assert normalize_description("TST* CANTEEN CAFE") == "CANTEEN CAFE"
    assert normalize_description("STRIPE *VERCEL") == "VERCEL"


def test_strip_store_and_ref_codes():
    assert normalize_description("BEST BUY #1049 REF#99823") == "BEST BUY"
    assert normalize_description("TARGET STORE 492 AUTH 938210") == "TARGET"
    assert normalize_description("UBER *TRIP CARD 1234") == "UBER TRIP"
    assert normalize_description("AMAZON.COM ACCT 9821") == "AMAZON.COM"


def test_strip_dates_and_locations():
    assert normalize_description("JETBRAINS 10/15/2024 SAN FRANCISCO CA") == "JETBRAINS"
    assert normalize_description("AWS 2024-08-01 SEATTLE WA US") == "AWS"


def test_symbol_replacements_and_whitespace():
    assert normalize_description("GOOGLE***WORKSPACE---CLOUD") == "GOOGLE WORKSPACE CLOUD"
    assert normalize_description("   SLACK   TECHNOLOGIES   ") == "SLACK TECHNOLOGIES"
    assert normalize_description("") == ""
    assert normalize_description(None) == ""
