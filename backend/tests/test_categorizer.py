import random
from decimal import Decimal

import pytest

from app.categories import DEDUCTIBLE, Category, sign_allows

C = Category


def decide(brain, description, amount, learned=None):
    return brain.categorize(description, Decimal(str(amount)), learned)


# (description, amount, expected category)
CASES = [
    # expenses
    ("SHELL PETROL STN #4421 LAHORE", -6500, C.FUEL),
    ("PSO FUEL 0091", -5200, C.FUEL),
    ("TOTAL PARCO FUEL 223", -3000, C.FUEL),
    ("M2 MOTORWAY TOLL PLAZA", -850, C.TOLLS_PARKING),
    ("CITY PARKING FEE 3321", -200, C.TOLLS_PARKING),
    ("AUTO WORKSHOP GULBERG", -4300, C.CAR_MAINTENANCE),
    ("JAZZ MOBILE BILL", -1200, C.PHONE_INTERNET),
    ("ZONG 4G INTERNET", -1500, C.PHONE_INTERNET),
    ("UBER SERVICE FEE", -2250, C.PLATFORM_FEES),
    ("FOODPANDA*ORDER 77812", -1450, C.PERSONAL),
    ("NETFLIX.COM", -1100, C.PERSONAL),
    # income and refunds: the same money-in sign, very different meaning
    ("UBER BV PAYOUT 88213", 45000, C.INCOME),
    ("CAREEM PAYOUT", 22000, C.INCOME),
    ("FOODPANDA PAYOUT 5512", 9800, C.INCOME),
    ("SHELL PETROL REFUND", 6500, C.REFUND),
    ("TOLL REVERSAL", 850, C.REFUND),
    # not spending
    ("TRANSFER TO SAVINGS", -10000, C.TRANSFER),
    ("TRANSFER FROM SAVINGS", 10000, C.TRANSFER),
    ("PAYMENT THANK YOU", -15000, C.CARD_PAYMENT),
    # unsure: must ask, never guess
    ("ATM CASH WITHDRAWAL", -5000, C.NEEDS_REVIEW),
    ("EASYPAISA TRANSFER 0099", -2000, C.NEEDS_REVIEW),
    ("JAZZCASH TOPUP", -500, C.NEEDS_REVIEW),  # JAZZ must not match inside JAZZCASH
    ("ALI TRADERS 5521", -3000, C.NEEDS_REVIEW),
    ("RANDOM DEPOSIT", 9000, C.NEEDS_REVIEW),
    ("FOODPANDA", -100, C.NEEDS_REVIEW),  # could be a payout or an order
    ("TRANSFER TO ALI KHAN", -8000, C.NEEDS_REVIEW),  # own account or paying someone?
    ("HBL SERVICE FEE", -100, C.NEEDS_REVIEW),  # bank fee, not a platform fee
    ("PSOLUTIONS PVT LTD", -100, C.NEEDS_REVIEW),  # PSO inside another word
    ("STOLLEN BAKERY", -100, C.NEEDS_REVIEW),  # TOLL inside another word
    ("SHELL DARAZ", -100, C.NEEDS_REVIEW),  # conflicting rules: Fuel vs Personal
    ("UBER BV PAYOUT", -500, C.NEEDS_REVIEW),  # payout but money went OUT: clawback?
    ("SHELL PETROL REFUND", -6500, C.NEEDS_REVIEW),  # refund wording but money went out
    ("UBER PAYOUT REFUND", 100, C.NEEDS_REVIEW),  # payout and refund wording together
    ("SHELL PETROL", 500, C.NEEDS_REVIEW),  # money in from a fuel station, no refund wording
    ("", -100, C.NEEDS_REVIEW),
    ("#### 12345", -100, C.NEEDS_REVIEW),
    ("SHELL", 0, C.NEEDS_REVIEW),
]


@pytest.mark.parametrize("description,amount,expected", CASES)
def test_category(brain, description, amount, expected):
    assert decide(brain, description, amount).category is expected


@pytest.mark.parametrize("description,amount,_", CASES)
def test_every_decision_explains_itself(brain, description, amount, _):
    decision = decide(brain, description, amount)
    assert decision.reason.strip()
    assert 0.0 <= decision.confidence <= 1.0


@pytest.mark.parametrize("description,amount,_", CASES)
def test_nothing_below_the_threshold_is_accepted(brain, description, amount, _):
    d = decide(brain, description, amount)
    if d.category is not C.NEEDS_REVIEW:
        assert d.confidence >= brain.rules.review_threshold


def test_refund_is_not_income_and_remembers_what_it_refunds(brain):
    d = decide(brain, "SHELL PETROL REFUND", 6500)
    assert d.category is C.REFUND
    assert d.related_category is C.FUEL


def test_review_rows_can_still_say_which_way_they_lean(brain):
    assert decide(brain, "TRANSFER TO ALI KHAN", -8000).suggestion is C.TRANSFER
    assert decide(brain, "HBL SERVICE FEE", -100).suggestion is C.PLATFORM_FEES
    assert decide(brain, "SHELL PETROL", 500).suggestion is C.REFUND


def test_unknown_merchant_has_no_suggestion(brain):
    assert decide(brain, "ALI TRADERS 5521", -3000).suggestion is None


# ---------------------------------------------------------------- learning


def test_what_the_user_taught_wins_over_keywords(brain):
    learned = {brain.normalize("SHELL PETROL STN"): C.PERSONAL}
    d = decide(brain, "SHELL PETROL STN #9 LAHORE", -100, learned)
    assert d.category is C.PERSONAL
    assert d.confidence == brain.rules.learned_confidence


def test_learned_memory_ignores_a_reference_number_change(brain):
    learned = {brain.normalize("ALI TRADERS 5521"): C.PERSONAL}
    assert decide(brain, "ALI TRADERS 7733", -50, learned).category is C.PERSONAL


def test_learned_category_is_ignored_when_the_money_direction_contradicts_it(brain):
    learned = {"ALI TRADERS": C.INCOME}
    assert decide(brain, "ALI TRADERS", 3000, learned).category is C.INCOME
    assert decide(brain, "ALI TRADERS", -3000, learned).category is C.NEEDS_REVIEW


def test_a_close_typo_of_a_learned_merchant_is_accepted(brain):
    learned = {"ALI TRADERS": C.PERSONAL}
    d = decide(brain, "ALI TRADER 9912", -50, learned)
    assert d.category is C.PERSONAL
    assert "similar" in d.reason


def test_a_loosely_similar_merchant_is_only_suggested(brain):
    learned = {"ALI TRADERS": C.PERSONAL}
    d = decide(brain, "ALI TRADER CO", -50, learned)
    assert d.category is C.NEEDS_REVIEW
    assert d.suggestion is C.PERSONAL


def test_a_different_merchant_is_not_matched_by_a_shared_word(brain):
    learned = {"ALI TRADERS": C.PERSONAL}
    assert decide(brain, "ALI MOTORS", -50, learned).category is C.NEEDS_REVIEW


def test_a_short_learned_name_does_not_swallow_longer_ones(brain):
    """token_set_ratio would score 100 here; token_sort_ratio does not."""
    learned = {"ALI": C.PERSONAL}
    assert decide(brain, "ALI AND SONS WORKSHOP SUPPLY", -50, learned).category is not C.PERSONAL


@pytest.mark.parametrize("description", ["ATM CASH WITHDRAWAL", "EASYPAISA 0099", "", "12345"])
def test_cash_and_empty_rows_are_never_learned(brain, description):
    assert not brain.is_learnable(description)


def test_ordinary_merchants_are_learnable(brain):
    assert brain.is_learnable("ALI TRADERS 5521")


# ---------------------------------------------------------------- invariants

WORDS = [
    "SHELL",
    "PSO",
    "TOLL",
    "PARKING",
    "JAZZ",
    "UBER",
    "CAREEM",
    "FOODPANDA",
    "PAYOUT",
    "ORDER",
    "REFUND",
    "REVERSAL",
    "TRANSFER",
    "TO",
    "FROM",
    "SAVINGS",
    "ATM",
    "CASH",
    "SERVICE",
    "FEE",
    "ALI",
    "TRADERS",
    "NETFLIX",
    "WORKSHOP",
    "PAYMENT",
    "THANK",
    "YOU",
    "1234",
    "#77",
    "*",
    "lahore",
]


def random_cases(n=3000):
    rng = random.Random(7)  # fixed seed: reproducible failures
    for _ in range(n):
        text = " ".join(rng.choice(WORDS) for _ in range(rng.randint(0, 5)))
        amount = Decimal(rng.choice([-1, 1])) * Decimal(rng.randint(1, 100_000)) / 100
        yield text, amount


def test_never_crashes_and_always_explains_on_random_input(brain):
    for text, amount in random_cases():
        d = brain.categorize(text, amount)
        assert d.reason.strip(), (text, amount)


def test_a_category_never_contradicts_the_direction_of_the_money(brain):
    """No 'Fuel' on money in, no 'Income' or 'Refund' on money out."""
    for text, amount in random_cases():
        d = brain.categorize(text, amount)
        assert sign_allows(d.category, amount), (text, amount, d)


def test_confident_decisions_are_never_below_the_threshold_on_random_input(brain):
    for text, amount in random_cases():
        d = brain.categorize(text, amount)
        if d.category is not C.NEEDS_REVIEW:
            assert d.confidence >= brain.rules.review_threshold, (text, amount, d)


def test_related_category_is_only_set_for_refunds(brain):
    for text, amount in random_cases():
        d = brain.categorize(text, amount)
        if d.related_category is not None:
            assert d.category is C.REFUND
            assert d.related_category in DEDUCTIBLE | {C.PERSONAL}


def test_gibberish_and_hostile_input_do_not_crash(brain):
    nasty = ["=cmd|' /C calc'!A0", "<script>alert(1)</script>", "\x00\x01", "💸" * 50, "A" * 10_000]
    for text in nasty:
        assert brain.categorize(text, Decimal(-10)).reason
