from datetime import date

import pytest

from app.engine.classifier import StatementRow, classify, classify_statement
from app.engine.rules import build_rules

REVIEW = "Needs Review"


# ---------------------------------------------------------------- happy paths


def test_adobe_is_software_with_high_confidence():
    result = classify("ADOBE CREATIVE CLOUD", -54.99)
    assert result.category == "Software & Subscriptions"
    assert result.confidence > 0.8
    assert result.source == "rule"
    assert result.reason == "Merchant 'ADOBE' matched Software & Subscriptions"
    assert not result.needs_review


def test_uber_trip_is_travel_after_normalization():
    result = classify("UBER *TRIP 8812", -23.40)
    assert result.category == "Travel"
    assert result.normalized_merchant == "UBER TRIP"


def test_more_specific_merchant_wins_uber_eats_is_meals():
    assert classify("UBER EATS 9921", -27.60).category == "Meals"


def test_keyword_match_has_keyword_confidence():
    result = classify("PIZZA PALACE 77", -22.50)
    assert (result.category, result.confidence) == ("Meals", 0.75)
    assert result.reason.startswith("Keyword 'PIZZA'")


def test_processor_prefix_is_removed_before_matching():
    assert classify("PAYPAL *ADOBE", -54.99).category == "Software & Subscriptions"


def test_keywords_match_whole_words_only():
    # "ADS" must not match inside "ROADSIDE"
    assert classify("ROADSIDE GRILL", -10).category == REVIEW


# ---------------------------------------------------------------- special cases


def test_refund_is_refund_not_income():
    result = classify("AMAZON REFUND", 30.00)
    assert result.category == "Refund"
    assert result.confidence == 0.95


def test_fee_reversal_is_a_refund():
    assert classify("LATE FEE REVERSAL", 25.00).category == "Refund"


def test_refund_wording_with_money_going_out_needs_review():
    result = classify("REFUND PROCESSING FEE", -5.00)
    assert result.category == REVIEW
    assert "money went out" in result.reason
    assert result.suggested_category == "Refund"


def test_transfer_to_savings_is_not_spending():
    result = classify("TRANSFER TO SAVINGS", -500.00)
    assert result.category == "Transfer (not spending)"


def test_transfer_in_either_direction():
    assert classify("ONLINE TRANSFER FROM CHECKING", 300).category == "Transfer (not spending)"


@pytest.mark.parametrize("desc", ["PAYMENT THANK YOU", "PAYMENT - THANK YOU", "AUTOPAY PAYMENT"])
def test_card_payment(desc):
    assert classify(desc, 800.00).category == "Card Payment (not spending)"


def test_card_payment_with_money_going_out_needs_review():
    assert classify("PAYMENT THANK YOU", -800.00).category == REVIEW


@pytest.mark.parametrize(
    "desc", ["ANNUAL FEE", "LATE FEE", "FX FEE", "FOREIGN TRANSACTION FEE", "INTEREST CHARGE"]
)
def test_bank_fees(desc):
    assert classify(desc, -25.00).category == "Bank Fees"


def test_generic_fee_keyword_is_bank_fees():
    assert classify("WIRE FEE", -15).category == "Bank Fees"


# ---------------------------------------------------------------- not sure -> Needs Review


def test_unknown_merchant_needs_review():
    result = classify("BLUE DOOR STUDIO", -140)
    assert result.category == REVIEW
    assert result.needs_review
    assert result.source == "none"
    assert result.confidence == 0.0
    assert result.reason == "No rule matched 'BLUE DOOR STUDIO'"


def test_joes_cafe_needs_review_with_weak_hint():
    result = classify("JOES CAFE 9921", -12.50)
    assert result.category == REVIEW
    assert result.confidence == 0.5
    assert result.suggested_category == "Meals"
    assert "weak hint" in result.reason


def test_weak_keyword_store_needs_review():
    result = classify("CORNER STORE 22", -9.99)
    assert result.category == REVIEW
    assert result.suggested_category == "Office Supplies"


def test_strong_merchant_beats_weak_keyword():
    assert classify("STARBUCKS STORE 1123", -6.75).category == "Meals"


def test_two_categories_tie_needs_review():
    result = classify("AMAZON MKTPLACE PMTS", -36.49)
    assert result.category == REVIEW
    assert result.reason.startswith("Multiple matches")
    assert "Office Supplies" in result.reason and "Personal" in result.reason
    assert result.confidence < 0.7


def test_positive_unknown_amount_is_not_guessed():
    result = classify("UNKNOWN CREDIT", 15.00)
    assert result.category == REVIEW
    assert "not guessing income or refund" in result.reason


def test_money_in_from_spending_merchant_without_refund_word_needs_review():
    result = classify("ADOBE CREATIVE CLOUD", 25.00)
    assert result.category == REVIEW
    assert result.suggested_category == "Software & Subscriptions"


def test_income_merchant():
    assert classify("UPWORK ESCROW PAYOUT", 1250).category == "Income"


def test_income_merchant_with_money_going_out_needs_review():
    assert classify("UPWORK ESCROW PAYOUT", -10).category == REVIEW


# ---------------------------------------------------------------- foreign currency


def test_foreign_currency_keeps_category_and_adds_note():
    result = classify("HOTEL LISBOA EUR 120.00", -131.40, currency="USD")
    assert result.category == "Travel"
    assert result.notes == ("Foreign currency: original charge 120.00 EUR",)


def test_same_currency_mention_is_just_a_note():
    result = classify("FIGMA USD 15.00", -15.0, currency="USD")
    assert result.category == "Software & Subscriptions"
    assert result.notes == ("Description mentions 15.00 USD",)


# ---------------------------------------------------------------- learning


def test_learned_rule_wins_with_full_confidence():
    result = classify("SQ *JOES CAFE 9921", -12.5, learned={"JOES CAFE": "Meals"})
    assert result.category == "Meals"
    assert result.confidence == 1.0
    assert result.source == "learned"


def test_learned_rule_overrides_special_rule_for_that_exact_merchant():
    result = classify("ZELLE TRANSFER TO ALI", -50, learned={"ZELLE TRANSFER TO ALI": "Personal"})
    assert result.category == "Personal"


def test_learned_rule_does_not_leak_to_other_merchants():
    assert classify("AMAZON REFUND", 30, learned={"AMAZON": "Office Supplies"}).category == "Refund"


# ---------------------------------------------------------------- duplicates


def _row(desc, amount, day=1, row_number=None):
    return StatementRow(date(2026, 5, day), desc, amount, "USD", row_number)


def test_duplicate_second_row_is_flagged():
    rows = [_row("STAPLES 00231", -48.2, row_number=9), _row("STAPLES 00231", -48.2, row_number=10)]
    first, second = classify_statement(rows)
    assert first.category == "Office Supplies" and not first.is_duplicate
    assert second.is_duplicate and second.needs_review
    assert second.category == REVIEW
    assert second.suggested_category == "Office Supplies"
    assert "Possible duplicate of row 9" in second.reason


def test_duplicate_detection_uses_normalized_merchant():
    rows = [_row("SQ *JOES CAFE", -9.25), _row("JOES CAFE 9921", -9.25)]
    assert classify_statement(rows)[1].is_duplicate


@pytest.mark.parametrize(
    "other",
    [
        _row("STAPLES 00231", -48.2, day=2),  # different date
        _row("STAPLES 00231", -48.3),  # different amount
        _row("OFFICE DEPOT", -48.2),  # different merchant
    ],
)
def test_not_duplicates(other):
    results = classify_statement([_row("STAPLES 00231", -48.2), other])
    assert not any(r.is_duplicate for r in results)


# ---------------------------------------------------------------- rules are data


def test_custom_rules_file_changes_behaviour_without_code_changes():
    rules = build_rules(
        {
            "threshold": 0.8,
            "confidence": {
                "learned": 1.0,
                "special": 0.95,
                "merchant": 0.9,
                "keyword": 0.75,
                "weak": 0.5,
            },
            "categories": {"Meals": {"keywords": ["CAFE"]}},
        }
    )
    # keyword confidence 0.75 is below this custom threshold of 0.8
    assert classify("JOES CAFE", -5, rules=rules).category == REVIEW
