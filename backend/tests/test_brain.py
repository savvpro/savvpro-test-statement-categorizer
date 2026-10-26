import pytest
from app.brain import Brain, normalize

b = Brain()


@pytest.mark.parametrize("raw,norm", [
    ("UBER *TRIP 8F3K2", "UBER TRIP"), ("STAPLES #0421", "STAPLES"), ("JOES CAFE 9921", "JOES CAFE"),
    ("AMZN MKTP US*2K4L9", "AMZN MKTP US"),
])
def test_normalize(raw, norm):
    assert normalize(raw) == norm


@pytest.mark.parametrize("desc,amount,category,review", [
    ("ADOBE CREATIVE CLOUD", -54.99, "Software", False),
    ("UBER *TRIP 8F3K2", -23.4, "Travel", False),
    ("UBER EATS HELP.UBER.COM", -31, "Meals", False),          # more specific beats UBER
    ("AMAZON WEB SERVICES", -10, "Hosting & Cloud", False),     # AWS is not 'Amazon'
    ("TRANSFER TO SAVINGS", -500, "Not Spending", False),
    ("AUTOPAY PAYMENT THANK YOU", 1200, "Not Spending", False),
    ("STARBUKS COFFEE 1182", -6.75, "Meals", False),            # typo, fuzzy
    ("FOREIGN TRANSACTION FEE", -1.2, "Bank Fees & Interest", False),
    ("JOES CAFE 9921", -12.5, "Needs Review", True),            # unknown
    ("AMZN MKTP US*2K4L9", -89.99, "Needs Review", True),       # ambiguous: never guess
    ("SQ *MARKET STALL", -18, "Needs Review", True),
    ("ZELLE TO MIKE", -200, "Needs Review", True),
    ("MYSTERY CREDIT", 25, "Needs Review", True),
    ("ACME CORP INVOICE 1042", 3500, "Income", False),
])
def test_categories(desc, amount, category, review):
    r = b.classify(desc, amount)
    assert (r.category, r.needs_review) == (category, review)


def test_refund_is_not_income():
    r = b.classify("STAPLES #0421 RETURN", 64.2)
    assert r.kind == "refund" and r.category == "Office & Equipment"


def test_refund_unknown_merchant_goes_to_review():
    assert b.classify("SOME SHOP REFUND", 20).needs_review


def test_user_rule_wins():
    br = Brain()
    br.learn("JOES CAFE", "Meals")
    r = br.classify("JOES CAFE 1234", -9)
    assert r.category == "Meals" and not r.needs_review
