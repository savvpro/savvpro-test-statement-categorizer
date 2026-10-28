from decimal import Decimal

import pytest

from app.brain import categorize
from app.domain.categories import NEEDS_REVIEW


def decide(desc: str, amount: str, learned=None):
    return categorize(desc, Decimal(amount), learned)


@pytest.mark.parametrize(
    "desc,amount,category",
    [
        ("UBER *PAYOUT DRIVER WEEKLY", "1284.50", "Platform Income"),
        ("DOORDASH DASHER DIRECT DEP", "612.75", "Platform Income"),
        ("LYFT DRIVER BONUS QUEST", "150.00", "Tips & Bonuses"),
        ("SHELL OIL 57444 DALLAS TX", "-48.20", "Fuel"),
        ("TESLA SUPERCHARGER US", "-18.42", "EV Charging"),
        ("JIFFY LUBE #1823 PLANO TX", "-89.99", "Vehicle Maintenance"),
        ("NTTA TOLLTAG REPLENISH", "-40.00", "Tolls & Parking"),
        ("T-MOBILE AUTOPAY", "-85.00", "Phone & Data"),
        ("GEICO AUTO INSURANCE", "-142.30", "Vehicle Insurance"),
        ("GRIDWISE PRO SUBSCRIPTION", "-9.99", "Business Apps & Fees"),
        ("MONTHLY SERVICE FEE", "-12.00", "Bank Fees"),
        ("PAYMENT THANK YOU-MOBILE", "650.00", "Card Payment"),
        ("ONLINE BANKING TRANSFER TO SAVINGS 7731", "-500.00", "Transfer"),
        ("NETFLIX.COM", "-15.49", "Personal"),
    ],
)
def test_clear_cases(desc, amount, category):
    d = decide(desc, amount)
    assert d.category == category
    assert d.confidence >= 0.75
    assert d.reason


def test_same_platform_money_in_is_income_but_money_out_is_a_meal():
    assert decide("DOORDASH DASHER DIRECT DEP", "612.75").category == "Platform Income"
    assert decide("DOORDASH*TACO SPOT", "-23.18").category == "Meals (Personal)"
    assert decide("DD *KITCHEN LUNCH BOX", "-18.60").category == "Meals (Personal)"


def test_order_credit_is_a_refund_not_income():
    assert decide("UBER EATS PROMOTION CREDIT", "10.00").category == "Refund"


def test_refund_is_money_back_not_income():
    d = decide("AUTOZONE #4410 REFUND", "24.99")
    assert d.category == "Refund"


def test_credit_from_a_known_shop_is_a_refund_even_without_the_word():
    assert decide("EXXONMOBIL 4471", "52.10").category == "Refund"


@pytest.mark.parametrize(
    "desc,amount,why",
    [
        ("SHELL OIL 57444", "-6.49", "snacks"),  # tiny fuel-station charge
        ("AMAZON MKTPLACE PMTS", "-34.99", "business and personal"),
        ("7-ELEVEN 33012", "-31.75", "business and personal"),
        ("ZELLE TO MARCUS R", "-75.00", "Peer-to-peer"),
        ("MOBILE DEPOSIT REF 88123", "300.00", "unknown source"),  # not income until confirmed
        ("UBER", "20.00", "not marked as a payout"),
        ("ACME WIDGETS LLC", "-19.99", "Unknown merchant"),
    ],
)
def test_unsure_rows_go_to_review_with_a_reason(desc, amount, why):
    d = decide(desc, amount)
    assert d.category == NEEDS_REVIEW
    assert why in d.reason


def test_review_keeps_a_suggestion():
    assert decide("SHELL OIL", "-6.49").suggestion == "Personal"


def test_learned_rule_wins():
    d = decide("JOES CAFE 0412", "-11.40", learned={"OUT:JOES CAFE": "Driver Supplies"})
    assert d.category == "Driver Supplies"
    assert d.rule == "learned"


def test_learned_rule_only_applies_in_the_same_direction():
    learned = {"OUT:EXXONMOBIL": "Transfer"}
    assert decide("EXXONMOBIL 4471", "-52.10", learned).category == "Transfer"
    assert decide("EXXONMOBIL 4471", "52.10", learned).category == "Refund"
