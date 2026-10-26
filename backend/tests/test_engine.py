from decimal import Decimal

import pytest

from app.brain import Categorizer, Flag, Source, TransactionInput
from app.brain.categories import CATEGORIES
from app.brain.knowledge import KEYWORD_RULES, MERCHANT_RULES, REFUND_MARKERS


def decide(description: str, amount: str, bank_category: str | None = None, **kwargs):
    return Categorizer(**kwargs).categorize(
        TransactionInput(description, Decimal(amount), bank_category)
    )


# --------------------------------------------------------------- clear-cut decisions
@pytest.mark.parametrize(
    ("description", "amount", "category"),
    [
        ("POS PURCHASE SHELL OIL 57444 SAN JOSE CA", "-45.20", "fuel"),
        ("COSTCO GAS #0144", "-58.77", "fuel"),
        ("TESLA SUPERCHARGER US PALO ALTO CA", "-18.40", "fuel"),
        ("UBER USA 6787 EDI PYMNTS PPD ID: 345", "612.33", "platform_income"),
        ("LYFT INC DIRECT DEP", "288.10", "platform_income"),
        ("DOORDASH DASHER DIRECT DEP", "402.18", "platform_income"),
        ("AMAZON FLEX PAYOUT", "120.00", "platform_income"),
        ("FASTRAK CSC 415-486-8655 CA", "-25.00", "tolls_parking"),
        ("SPOTHERO 8558 NEW YORK NY", "-14.00", "tolls_parking"),
        ("GEICO *AUTO 800-841-3000 DC", "-142.18", "vehicle_insurance"),
        ("T-MOBILE *AUTOPAY 800-937-8997 WA", "-85.00", "phone_data"),
        (
            "PURCHASE AUTHORIZED ON 01/10 JIFFY LUBE #1234 CARD 0000",
            "-79.99",
            "vehicle_maintenance",
        ),
        ("GRIDWISE PLUS SUBSCRIPTION", "-9.99", "software_services"),
        ("DMV RENEWAL VEHICLE REGISTRATION", "-238.00", "licenses_fees"),
        ("CHECKR INC SAN FRANCISCO CA", "-30.00", "licenses_fees"),
        ("FOREIGN TRANSACTION FEE", "-1.20", "bank_fees"),
        ("INTEREST CHARGE ON PURCHASES", "-14.32", "bank_fees"),
        ("KROGER #0412 SAN JOSE CA", "-86.42", "personal"),
        ("NETFLIX.COM LOS GATOS CA", "-15.49", "personal"),
        ("UBER *EATS HELP.UBER.COM", "-31.00", "personal"),
        ("UBER *TRIP HELP.UBER.COM", "-18.40", "personal"),
        ("TRANSFER TO SAVINGS XXXXXX1234", "-500.00", "transfer"),
        ("ONLINE TRANSFER FROM SAVINGS", "500.00", "transfer"),
        ("PAYMENT THANK YOU-MOBILE", "800.00", "transfer"),
        ("CHASE CREDIT CRD AUTOPAY PPD ID: 476", "-800.00", "transfer"),
        ("ATM WITHDRAWAL 000123 MAIN ST", "-60.00", "transfer"),
    ],
)
def test_known_transactions_are_categorised(description, amount, category):
    d = decide(description, amount)
    assert d.category == category, d.reasons
    assert not d.needs_review
    assert d.confidence >= 0.75


# ---------------------------------------------------------- "not sure" goes to review
@pytest.mark.parametrize(
    ("description", "amount", "first_suggestion"),
    [
        ("SQ *JOES CAFE 9921", "-6.75", "personal"),  # only a weak keyword
        ("AMAZON.COM*2K4LM19QX AMZN.COM/BILL WA", "-39.99", "supplies"),  # mixed store
        ("ZELLE PAYMENT TO MIKES AUTO SHOP", "-300.00", "personal"),  # person-to-person
        ("UBER BV", "25.00", "platform_income"),  # payout or customer refund?
        ("MOBILE DEPOSIT", "150.00", "other_income"),
        ("TOYOTA FINANCIAL SVCS PMT", "-389.00", "vehicle_lease_loan"),  # lease vs loan
        ("CHEVRN 0091 FRESNO CA", "-52.10", "fuel"),  # typo - fuzzy match only
        ("7-ELEVEN 33421", "-6.10", "fuel"),
    ],
)
def test_uncertain_transactions_go_to_review(description, amount, first_suggestion):
    d = decide(description, amount)
    assert d.needs_review
    assert d.category is None
    assert d.suggestions[0] == first_suggestion


def test_unknown_merchant_is_never_guessed():
    d = decide("LUCKY STAR TRADING LLC", "-42.00")
    assert d.needs_review and d.category is None and d.source is Source.NONE


def test_unknown_deposit_is_not_counted_as_income():
    d = decide("ACME HOLDINGS 4471", "200.00")
    assert d.needs_review and d.category is None
    assert Flag.UNKNOWN_DEPOSIT in d.flags
    assert "not counted as income" in " ".join(d.reasons)


# ------------------------------------------------------------------------- refunds
def test_refund_reduces_the_expense_category_not_income():
    d = decide("AUTOZONE #3321 RETURN", "24.00")
    assert d.category == "vehicle_maintenance"
    assert Flag.REFUND in d.flags
    assert not d.needs_review


def test_money_back_without_refund_word_is_still_a_refund_with_lower_confidence():
    marked = decide("JIFFY LUBE REFUND", "20.00")
    unmarked = decide("JIFFY LUBE", "20.00")
    assert unmarked.category == "vehicle_maintenance"
    assert Flag.REFUND in unmarked.flags
    assert unmarked.confidence < marked.confidence


def test_refund_from_ambiguous_store_asks_which_category():
    d = decide("AMAZON.COM REFUND", "19.99")
    assert d.needs_review and Flag.REFUND in d.flags


def test_refund_from_unknown_merchant_asks():
    d = decide("SOME SHOP REFUND", "10.00")
    assert d.needs_review and Flag.REFUND in d.flags


def test_fee_reversal_reduces_fees():
    d = decide("MONTHLY SERVICE FEE REVERSAL", "12.00")
    assert d.category == "bank_fees" and Flag.REFUND in d.flags


def test_card_rewards_are_not_income():
    d = decide("CASH BACK REWARD REDEMPTION", "25.00")
    assert d.category == "personal"


# ------------------------------------------------------------------ messy edge cases
def test_tmobile_is_not_mobil_gas():
    assert decide("T-MOBILE", "-60.00").category == "phone_data"
    assert decide("MOBIL 0042", "-40.00").category == "fuel"


def test_phone_autopay_is_not_a_card_payment():
    assert decide("VERIZON WIRELESS AUTOPAY", "-70.00").category == "phone_data"


def test_small_gas_station_purchase_could_be_snacks():
    d = decide("SHELL OIL 57444", "-4.50")
    assert d.needs_review and Flag.SMALL_AMOUNT in d.flags
    assert d.suggestions[:2] == ["fuel", "personal"]


def test_unusually_large_amount_goes_to_review():
    d = decide("SHELL OIL 57444", "-412.00")
    assert d.needs_review and Flag.LARGE_AMOUNT in d.flags


def test_parking_fine_is_not_deductible_parking():
    assert decide("PARKING CITATION CITY OF OAKLAND", "-64.00").category == "personal"


def test_conflicting_evidence_goes_to_review():
    d = decide("SHELL CAR WASH", "-12.00")
    assert d.needs_review
    assert set(d.suggestions) >= {"fuel", "vehicle_maintenance"}


def test_keyword_can_resolve_an_ambiguous_store():
    d = decide("7-ELEVEN FUEL 33421", "-41.10")
    assert d.category == "fuel" and not d.needs_review


def test_zelle_transfer_wording_is_not_an_own_account_transfer():
    d = decide("ZELLE TRANSFER TO JOHN DOE", "-50.00")
    assert d.needs_review


def test_bank_category_agreement_lifts_a_weak_keyword():
    without = decide("SQ *JOES CAFE 9921", "-6.75")
    with_hint = decide("SQ *JOES CAFE 9921", "-6.75", bank_category="Food & Drink")
    assert without.needs_review
    assert with_hint.category == "personal" and not with_hint.needs_review


def test_bank_category_alone_is_not_enough():
    d = decide("ZQX STATION 44", "-30.00", bank_category="Gas")
    assert d.needs_review and d.suggestions == ["fuel"]


def test_income_platform_money_out_is_flagged():
    rules = {("uber usa edi pymnts", "out"): "platform_income"}
    d = decide("UBER USA EDI PYMNTS", "-50.00", user_rules=rules)
    assert d.needs_review and Flag.DIRECTION_MISMATCH in d.flags


# --------------------------------------------------------------------- user rules
def test_user_rule_beats_knowledge_base():
    rules = {("starbucks", "out"): "supplies"}
    d = decide("STARBUCKS", "-5.00", user_rules=rules)
    assert d.category == "supplies" and d.source is Source.USER_RULE


def test_user_rule_is_direction_specific():
    rules = {("joes cafe", "out"): "personal"}
    d = decide("JOES CAFE", "6.75", user_rules=rules)
    assert d.source is not Source.USER_RULE


def test_user_rule_still_gets_amount_check():
    rules = {("shell oil", "out"): "fuel"}
    d = decide("SHELL OIL", "-450.00", user_rules=rules)
    assert d.needs_review and Flag.LARGE_AMOUNT in d.flags


def test_threshold_is_configurable():
    assert not decide("SQ *JOES CAFE", "-6.75", threshold=0.6).needs_review


# ------------------------------------------------------------- knowledge integrity
def test_every_rule_points_at_a_real_category():
    ids = {c.id for c in CATEGORIES}
    for rule in MERCHANT_RULES:
        assert rule.category is None or rule.category in ids, rule.name
        assert all(s in ids for s in rule.suggestions), rule.name
        assert rule.ambiguous == (rule.category is None)
    for kw in KEYWORD_RULES:
        assert kw.category in ids


def test_ambiguous_rules_always_offer_suggestions():
    for rule in MERCHANT_RULES:
        if rule.ambiguous:
            assert rule.suggestions, rule.name


def test_refund_marker_regex():
    assert REFUND_MARKERS.search("AMAZON REFUND")
    assert not REFUND_MARKERS.search("SHELL OIL")
