from app.categorization.normalizer import merchant_key, normalize
from app.domain.models import Category
from app.learning.repository import MerchantRule

from .conftest import make_tx


def one(engine, description, amount):
    return engine.categorize([make_tx(2, description, amount)])[0]


def test_normalize_strips_prefixes_and_references():
    assert normalize("CARD PAYMENT TO UBER *TRIP 8812 ON 03 MAR") == "UBER TRIP"
    assert merchant_key(normalize("TRAINLINE.COM REFUND 77731")) == "TRAINLINE"


def test_known_merchants(engine):
    assert one(engine, "ADOBE *CREATIVE CLOUD", "-54.99").category == Category.SOFTWARE
    assert one(engine, "CARD PAYMENT TO UBER *TRIP 8812", "-18.40").category == Category.TRAVEL
    assert one(engine, "NETFLIX.COM", "-10.99").category == Category.PERSONAL
    assert one(engine, "HMRC SELF ASSESSMENT", "-1250").category == Category.TAX


def test_every_decision_is_explained(engine):
    result = one(engine, "GITHUB INC", "-9")
    assert result.reasons and 0 < result.confidence <= 1


def test_unknown_merchant_goes_to_review(engine):
    result = one(engine, "JOES CAFE 9921", "-7.80")
    assert result.category == Category.NEEDS_REVIEW and result.confidence == 0


def test_transfers_are_not_spending_or_income(engine):
    assert one(engine, "TRANSFER TO SAVINGS", "-500").category == Category.TRANSFER
    assert one(engine, "TRANSFER FROM J DOE", "300").category == Category.TRANSFER


def test_mixed_use_merchant_is_never_guessed(engine):
    assert one(engine, "AMAZON MKTPLACE PMTS", "-39.99").category == Category.NEEDS_REVIEW


def test_refund_is_matched_and_nets_off_the_expense(engine):
    purchase, refund = engine.categorize([
        make_tx(2, "TRAINLINE.COM 77731", "-64.20", 3), make_tx(3, "TRAINLINE.COM REFUND", "64.20", 8)])
    assert refund.category == Category.TRAVEL and refund.refund_of == purchase.row


def test_refund_before_purchase_is_not_matched(engine):
    refund, _ = engine.categorize([make_tx(2, "TRAINLINE REFUND", "10", 1), make_tx(3, "TRAINLINE", "-10", 5)])
    assert refund.category == Category.REFUND and refund.refund_of is None


def test_purchase_is_refunded_only_once(engine):
    results = engine.categorize([
        make_tx(2, "TRAINLINE", "-10", 1), make_tx(3, "TRAINLINE REFUND", "10", 2),
        make_tx(4, "TRAINLINE REFUND", "10", 3)])
    assert results[1].refund_of == 2 and results[2].refund_of is None


def test_unexplained_credit_needs_review_with_suggestion(engine):
    result = one(engine, "UNKNOWN CREDIT", "75")
    assert result.category == Category.NEEDS_REVIEW and result.suggestion == Category.INCOME


def test_client_payment_is_income(engine):
    assert one(engine, "FASTER PAYMENT FROM ACME INV 1042", "2400").category == Category.INCOME


def test_interest_received_is_not_income(engine):
    assert one(engine, "INTEREST PAID", "1.12").category == Category.NEEDS_REVIEW


def test_duplicate_is_flagged(engine):
    first, second = engine.categorize([make_tx(2, "GITHUB INC", "-9", 7), make_tx(3, "GITHUB INC", "-9", 7)])
    assert first.category == Category.SOFTWARE
    assert second.category == Category.NEEDS_REVIEW and "duplicate" in second.flags


def test_conflicting_signals_go_to_review(engine):
    result = one(engine, "SHELL TESCO EXPRESS", "-10")
    assert result.category == Category.NEEDS_REVIEW and result.suggestion is not None


def test_weak_match_becomes_review_with_suggestion(engine):
    result = one(engine, "ANNUAL SUBSCRIPTION", "-10")
    assert result.category == Category.NEEDS_REVIEW and result.suggestion == Category.SOFTWARE


def test_large_purchase_flagged(engine):
    assert "large-amount" in one(engine, "RYMAN STATIONERY", "-1500").flags
    assert "large-amount" not in one(engine, "HMRC SELF ASSESSMENT", "-1500").flags


def test_recurring_payments_detected(engine):
    results = engine.categorize([
        make_tx(2, "GITHUB INC", "-9", 7, 1), make_tx(3, "GITHUB INC", "-9", 7, 2), make_tx(4, "UDEMY", "-15", 7, 2)])
    assert ["recurring" in r.flags for r in results] == [True, True, False]


def test_learned_rule_overrides_built_in_knowledge(engine, repository):
    repository.save(MerchantRule("JOES CAFE", Category.TRAVEL))
    result = one(engine, "JOES CAFE 9921", "-7.80")
    assert result.category == Category.TRAVEL and "learned" in result.flags


def test_learned_rule_ignored_when_direction_does_not_fit(engine, repository):
    repository.save(MerchantRule("TRAINLINE", Category.TRAVEL))
    assert one(engine, "TRAINLINE REFUND", "10").category == Category.REFUND


def test_results_keep_statement_order(engine):
    results = engine.categorize([make_tx(5, "GITHUB", "-9", 20), make_tx(2, "ADOBE", "-5", 1)])
    assert [r.row for r in results] == [5, 2]
