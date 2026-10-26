import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from app.brain.categorizer import Categorizer
from app.brain.normalize import normalize
from app.models import Category, RawTransaction
from app.parsing.csv_parser import parse_statement

DATA = Path(__file__).parent.parent / "data"
brain = Categorizer()


def decide(description: str, amount: str):
    _, (category, confidence, explanation) = brain.decide(description, Decimal(amount))
    return category, confidence, explanation


# ---------------------------------------------------------------- normalize
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("ELECTRIC CO *AUTOPAY", "ELECTRIC CO"),
        ("ACE PLUMBING 4412", "ACE PLUMBING"),
        ("TRANSFER TO SAVINGS ****1234", "TRANSFER TO SAVINGS"),
        ("  joes   cafe 9921 ", "JOES CAFE"),
        ("POS PURCHASE HOME DEPOT #0117 03/04", "HOME DEPOT"),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


# ------------------------------------------------- one test per edge case
def test_rent_in_is_rental_income():
    category, confidence, _ = decide("ZELLE FROM JOHN TENANT", "1500.00")
    assert category == Category.RENTAL_INCOME and confidence >= 0.75


def test_partial_rent_payments_are_both_income():
    assert decide("ZELLE FROM JOHN TENANT", "750.00")[0] == Category.RENTAL_INCOME


def test_security_deposit_received_is_not_income():
    category, _, why = decide("ZELLE FROM NEW TENANT SEC DEPOSIT", "1500.00")
    assert category == Category.SECURITY_DEPOSIT
    assert "received" in why


def test_security_deposit_returned_is_not_an_expense():
    category, _, why = decide("CHECK 1042 DEPOSIT REFUND", "-1500.00")
    assert category == Category.SECURITY_DEPOSIT
    assert "returned" in why


def test_refund_is_negative_expense_not_income():
    category, _, why = decide("ACE PLUMBING REFUND", "120.00")
    assert category == Category.REPAIRS
    assert "not income" in why


def test_transfer_is_not_spending():
    assert decide("TRANSFER TO SAVINGS ****1234", "-500.00")[0] == Category.TRANSFER


def test_mortgage_needs_review_until_loan_details_exist():
    category, _, why = decide("WELLS FARGO HOME MTG PYMT", "-1199.10")
    assert category == Category.NEEDS_REVIEW
    assert "interest and principal" in why


@pytest.mark.parametrize(
    "description", ["HOME DEPOT 0117", "AMAZON MKTPLACE PMTS", "LOWES #1234"]
)
def test_ambiguous_merchants_are_never_guessed(description):
    assert decide(description, "-50.00")[0] == Category.NEEDS_REVIEW


def test_unknown_merchant_needs_review():
    category, confidence, _ = decide("JOES CAFE 9921", "-18.50")
    assert category == Category.NEEDS_REVIEW and confidence == 0.0


# ------------------------------------------------------------ extra safety
def test_weak_evidence_goes_to_review():
    # "ZELLE FROM <someone>" alone could be anything.
    assert decide("ZELLE FROM BOB SMITH", "300.00")[0] == Category.NEEDS_REVIEW


def test_rent_keyword_does_not_match_inside_other_words():
    assert decide("CURRENT ACCOUNT NOTICE", "100.00")[0] == Category.NEEDS_REVIEW


def test_conflicting_evidence_goes_to_review():
    category, _, why = decide("WATER HEATER REPAIR CO", "-400.00")
    assert category == Category.NEEDS_REVIEW
    assert "Conflicting" in why


def test_money_in_from_expense_merchant_without_refund_word_is_review():
    assert decide("CITY WATER UTILITY", "50.00")[0] == Category.NEEDS_REVIEW


def test_money_out_is_never_rental_income():
    assert decide("PAYMENT TO TENANT SERVICES", "-100.00")[0] != Category.RENTAL_INCOME


def test_typo_is_still_recognised_with_lower_confidence():
    exact = decide("ACE PLUMBING", "-100.00")
    typo = decide("ACE PLUMBNG", "-100.00")
    assert typo[0] == Category.REPAIRS
    assert typo[1] < exact[1]


def test_learning_a_correction_applies_to_similar_rows():
    local = Categorizer()
    assert local.decide("JOES CAFE 9921", Decimal("-18.50"))[1][0] == Category.NEEDS_REVIEW
    local.learn("JOES CAFE 9921", Category.REPAIRS)
    category, confidence, _ = local.decide("JOES CAFE 1234", Decimal("-9.00"))[1]
    assert category == Category.REPAIRS and confidence == 1.0


def test_cannot_learn_needs_review():
    with pytest.raises(ValueError):
        Categorizer().learn("X", Category.NEEDS_REVIEW)


def test_duplicates_are_flagged_not_dropped():
    tx = lambda n: RawTransaction(
        row_number=n, date=dt.date(2025, 8, 22),
        description="LOCKSMITH EXPRESS 220", amount=Decimal("-85.00"),
    )
    first, second = brain.categorize_all([tx(2), tx(3)])
    assert not first.is_duplicate
    assert second.is_duplicate and "row 2" in second.explanation


# --------------------------------------------------- whole sample statement
def test_sample_statement_end_to_end():
    parsed = parse_statement((DATA / "bank_a.csv").read_bytes())
    results = brain.categorize_all(parsed.transactions)
    assert len(results) == len(parsed.transactions)

    review = {t.normalized for t in results if t.needs_review}
    assert {"HOME DEPOT", "AMAZON MKTPLACE PMTS", "JOES CAFE"} <= review

    # Nothing that is clearly rent or tax was sent to review.
    for t in results:
        if "TENANT" in t.normalized and "DEPOSIT" not in t.normalized:
            assert t.category == Category.RENTAL_INCOME
        if "PROPERTY TAX" in t.normalized:
            assert t.category == Category.PROPERTY_TAX

    assert sum(t.is_duplicate for t in results) == 1
    assert all(0 <= t.confidence <= 1 and t.explanation for t in results)