import pytest

from categorizer import CATEGORIES, categorize_transaction, parse_amount


def result(description, amount):
    r = categorize_transaction(description, amount)
    return r["category"], r["kind"]


def test_known_software():
    assert result("ADOBE CREATIVE CLOUD", 60) == ("Software", "expense")


def test_travel():
    assert result("UBER TRIP", 25) == ("Travel", "expense")


def test_uber_eats_is_meals_not_travel():
    assert result("UBER EATS ORDER", 20) == ("Meals", "expense")
    assert result("UBEREATS", 20) == ("Meals", "expense")


def test_word_boundaries_prevent_false_matches():
    # "training" must not match "train"
    assert result("TRAINING COURSE UDEMY", 20) == ("Education & Training", "expense")
    assert result("RANDOM TRAINING INC", 20)[0] == "Needs Review"


def test_unknown_merchant_needs_review():
    assert result("JOES CAFE 9921", 18) == ("Needs Review", "review")


def test_blank_and_zero_need_review():
    assert result("", 10)[0] == "Needs Review"
    assert result("ADOBE", 0)[0] == "Needs Review"


@pytest.mark.parametrize("desc,amount", [
    ("TRANSFER TO SAVINGS", 500),
    ("TRANSFER TO SAVINGS", -500),
    ("PAYMENT THANK YOU", -500),
    ("CREDIT CARD PAYMENT", 300),
])
def test_transfers_are_not_spending(desc, amount):
    assert result(desc, amount) == ("Transfer", "transfer")


def test_refund_is_not_income():
    assert result("REFUND ADOBE", -10) == ("Software", "refund")


def test_refund_with_unknown_merchant_needs_review():
    assert result("REFUND FROM MYSTERY LLC", -10)[0] == "Needs Review"


def test_refund_wording_with_positive_amount_needs_review():
    assert result("REFUND ADOBE", 10)[0] == "Needs Review"


def test_negative_amount_without_refund_wording_needs_review():
    assert result("ADOBE", -10)[0] == "Needs Review"


def test_income():
    assert result("CLIENT PAYMENT", 1200) == ("Income", "income")
    assert result("Stripe payout", 900) == ("Income", "income")


def test_income_wording_with_negative_amount_needs_review():
    assert result("CLIENT PAYMENT", -100)[0] == "Needs Review"


def test_conflicting_categories_need_review():
    assert result("INTERNET TRANSFER FEE", 3)[0] == "Needs Review"
    assert result("MONTHLY FEE ADOBE", 5)[0] == "Needs Review"


def test_same_category_multiple_keywords_is_fine():
    assert result("HOTEL TAXI", 10) == ("Travel", "expense")


def test_description_whitespace_and_case():
    assert result("  adobe   creative   cloud ", 60) == ("Software", "expense")


def test_every_rule_category_is_listed():
    from categorizer import EXPENSE_RULES
    assert all(cat in CATEGORIES for cat, _ in EXPENSE_RULES)


@pytest.mark.parametrize("raw,expected", [
    ("$1,234.50", 1234.50),
    ("(25.00)", -25.00),
    ("-$10", -10.00),
    ("$-10", -10.00),
    ("25.00 CR", -25.00),
    ("25.00 DR", 25.00),
    (" 7 ", 7.00),
])
def test_amount_formats(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "", "nan", "inf"])
def test_bad_amounts_raise(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)
