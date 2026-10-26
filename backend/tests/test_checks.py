from app.brain.checks.currency import check_currency
from app.brain.checks.income import check_income
from app.brain.checks.keyword import check_keyword
from app.brain.checks.refund import check_refund
from app.brain.checks.transfer import check_transfer
from app.brain.result import INCOME, NEEDS_REVIEW, REFUND, TRANSFER


# ---- transfer ----
def test_transfer_detected(make_txn, rules):
    d = check_transfer(make_txn("TRANSFER TO SAVINGS", -500), rules)
    assert d.category == TRANSFER


def test_transfer_needs_whole_word(make_txn, rules):
    assert check_transfer(make_txn("RETRANSFERRED FUNDS", -5), rules) is None


def test_card_payment_is_transfer(make_txn, rules):
    d = check_transfer(make_txn("CREDIT CARD PAYMENT THANK YOU", -1000), rules)
    assert d.category == TRANSFER


# ---- refund ----
def test_refund_money_in_is_refund_not_income(make_txn, rules):
    d = check_refund(make_txn("AMAZON REFUND", 29.99), rules)
    assert d.category == REFUND
    assert d.confidence == "high"


def test_refund_word_but_money_out_needs_review(make_txn, rules):
    d = check_refund(make_txn("REFUND TO CUSTOMER", -20), rules)
    assert d.category == NEEDS_REVIEW
    assert d.confidence == "low"


def test_no_refund_word_returns_none(make_txn, rules):
    assert check_refund(make_txn("ADOBE", -5), rules) is None


# ---- income ----
def test_income_money_in(make_txn, rules):
    assert check_income(make_txn("CLIENT PAYMENT ACME", 1200), rules).category == INCOME


def test_income_keyword_but_money_out_is_not_income(make_txn, rules):
    assert check_income(make_txn("CLIENT LUNCH", -40), rules) is None


# ---- keyword ----
def test_keyword_software(make_txn, rules):
    d = check_keyword(make_txn("ADOBE CREATIVE CLOUD", -54.99), rules)
    assert d.category == "Software"
    assert d.confidence == "high"


def test_longest_keyword_wins(make_txn, rules):
    assert check_keyword(make_txn("UBER EATS", -20), rules).category == "Meals"
    assert check_keyword(make_txn("UBER TRIP", -20), rules).category == "Travel"


def test_ambiguous_merchant_needs_review(make_txn, rules):
    d = check_keyword(make_txn("AMAZON MKTP", -45), rules)
    assert d.category == NEEDS_REVIEW
    assert d.confidence == "low"


def test_expense_merchant_with_money_in_needs_review(make_txn, rules):
    d = check_keyword(make_txn("ADOBE SYSTEMS", 20), rules)
    assert d.category == NEEDS_REVIEW


def test_unknown_merchant_returns_none(make_txn, rules):
    assert check_keyword(make_txn("JOES CAFE", -12.4), rules) is None


# ---- currency ----
def test_foreign_currency_needs_review(make_txn, rules):
    d = check_currency(make_txn("ADOBE", -5, currency="EUR"), rules)
    assert d.category == NEEDS_REVIEW
    assert "EUR" in d.reason


def test_base_currency_passes(make_txn, rules):
    assert check_currency(make_txn("ADOBE", -5), rules) is None