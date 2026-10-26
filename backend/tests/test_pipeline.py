from decimal import Decimal

import pytest

from app.brain.categories import NEEDS_REVIEW
from app.brain.pipeline import categorize
from app.config import Settings
from app.domain.models import Convention, Flag, Kind, Status
from app.parsing.csv_reader import read_csv


def run(classifier, csv_text: str, convention=None, settings=None):
    parsed = read_csv(csv_text.encode(), max_rows=5000)
    result = categorize(parsed, classifier, settings or Settings(), convention)
    return result, {t.description: t for t in result.transactions}


HEADER = "Date,Description,Amount\n"


def test_refund_takes_the_category_of_the_purchase_it_reverses(classifier):
    result, by = run(
        classifier,
        HEADER
        + "2026-03-01,ADOBE *CREATIVE CLOUD,54.99\n2026-03-12,ADOBE REFUND CREATIVE CLOUD,-54.99\n"
        "2026-03-20,ONLINE PAYMENT - THANK YOU,-100.00\n",
    )
    purchase, refund = result.transactions[0], result.transactions[1]
    assert refund.category_id == purchase.category_id == "software"
    assert refund.refund_of == purchase.id
    assert Flag.REFUND in refund.flags
    assert refund.kind is Kind.EXPENSE  # it is not income
    assert refund.spend_amount == Decimal("-54.99")
    assert "Refund of" in refund.reasons[0]


def test_partial_refund_leaves_the_rest_available(classifier):
    result, _ = run(
        classifier,
        HEADER
        + "2026-03-01,STAPLES 0042,64.30\n2026-03-05,STAPLES RETURN,-24.30\n2026-03-06,STAPLES RETURN,-30.00\n",
    )
    first, second = result.transactions[1], result.transactions[2]
    assert first.refund_of == second.refund_of == result.transactions[0].id


def test_refund_larger_than_the_purchase_is_not_matched(classifier):
    result, _ = run(
        classifier, HEADER + "2026-03-01,STAPLES 0042,10.00\n2026-03-05,STAPLES RETURN,-50.00\n"
    )
    refund = result.transactions[1]
    assert refund.refund_of is None
    assert Flag.UNMATCHED_REFUND in refund.flags


def test_refund_must_not_come_before_the_purchase(classifier):
    result, _ = run(
        classifier, HEADER + "2026-03-10,STAPLES RETURN,-10.00\n2026-03-20,STAPLES 0042,10.00\n"
    )
    assert result.transactions[0].refund_of is None


def test_refund_from_known_merchant_without_the_purchase_still_gets_its_category(classifier):
    result, _ = run(
        classifier, HEADER + "2026-03-05,FIGMA REFUND,-12.00\n2026-03-06,STAPLES 0042,5.00\n"
    )
    refund = result.transactions[0]
    assert refund.category_id == "software"
    assert refund.status is Status.CATEGORIZED
    assert Flag.UNMATCHED_REFUND in refund.flags
    assert refund.confidence <= 0.8
    assert "earlier statement" in " ".join(refund.reasons)


def test_refund_from_unknown_merchant_goes_to_review(classifier):
    result, _ = run(
        classifier, HEADER + "2026-03-05,MYSTERY SHOP REFUND,-12.00\n2026-03-06,STAPLES 0042,5.00\n"
    )
    refund = result.transactions[0]
    assert refund.category_id == NEEDS_REVIEW
    assert Flag.REFUND in refund.flags


def test_refund_of_an_ambiguous_purchase_is_also_ambiguous(classifier):
    result, _ = run(
        classifier,
        HEADER
        + "2026-03-01,AMZN MKTP US*AB12CD34,30.00\n2026-03-04,AMZN MKTP US*ZZ99YY88 REFUND,-30.00\n",
    )
    assert [t.status for t in result.transactions] == [Status.NEEDS_REVIEW, Status.NEEDS_REVIEW]
    assert result.transactions[1].refund_of == result.transactions[0].id


def test_money_in_is_never_labelled_income_without_evidence(classifier):
    result, _ = run(
        classifier, HEADER + "2026-03-05,SOMETHING ODD,-80.00\n2026-03-06,STAPLES 0042,5.00\n"
    )
    assert result.transactions[0].kind is not Kind.INCOME


def test_identical_lines_are_flagged_as_possible_duplicates(classifier):
    result, _ = run(
        classifier,
        HEADER
        + "2026-03-05,STARBUCKS 1,6.85\n2026-03-05,STARBUCKS 2,6.85\n2026-03-06,STARBUCKS 1,6.85\n",
    )
    flags = [t.flags for t in result.transactions]
    assert Flag.POSSIBLE_DUPLICATE not in flags[0]
    assert Flag.POSSIBLE_DUPLICATE in flags[1]
    assert Flag.POSSIBLE_DUPLICATE not in flags[2]  # different day
    assert any("duplicates" in w for w in result.warnings)


def test_duplicates_keep_their_category(classifier):
    result, _ = run(
        classifier, HEADER + "2026-03-05,STARBUCKS 1,6.85\n2026-03-05,STARBUCKS 1,6.85\n"
    )
    assert {t.category_id for t in result.transactions} == {"meals"}


def test_foreign_currency_rows_are_never_totalled_blindly(classifier):
    result, _ = run(
        classifier,
        "Date,Description,Amount,Currency\n2026-03-05,UBER TRIP,10.00,USD\n2026-03-06,UBER TRIP,12.00,USD\n"
        "2026-03-07,UBER TRIP,14.30,EUR\n",
    )
    assert result.currency == "USD"
    foreign = result.transactions[2]
    assert foreign.status is Status.NEEDS_REVIEW
    assert Flag.FOREIGN_CURRENCY in foreign.flags
    assert foreign.suggestions == ("travel",)
    assert "not converted" in " ".join(foreign.reasons)


def test_low_confidence_never_becomes_a_category(classifier):
    result, by = run(classifier, HEADER + "2026-03-05,SQ *JOES CAFE 9921,12.50\n")
    txn = by["SQ *JOES CAFE 9921"]
    assert txn.status is Status.NEEDS_REVIEW
    assert txn.category_id == NEEDS_REVIEW
    assert txn.suggestions == ("meals",)


def test_threshold_is_configurable(classifier):
    strict = Settings(review_threshold=0.99)
    result, _ = run(
        classifier, HEADER + "2026-03-05,ADOBE *CREATIVE CLOUD,54.99\n", settings=strict
    )
    txn = result.transactions[0]
    assert txn.status is Status.NEEDS_REVIEW
    assert txn.suggestions == ("software",)
    assert "below" in txn.reasons[-1]


def test_large_amounts_are_flagged_but_still_categorized(classifier):
    result, _ = run(classifier, HEADER + "2026-03-05,WEWORK MEMBERSHIP,1500.00\n")
    txn = result.transactions[0]
    assert Flag.LARGE_AMOUNT in txn.flags
    assert txn.status is Status.CATEGORIZED


def test_non_spending_rows_are_excluded(classifier):
    result, _ = run(
        classifier,
        HEADER
        + "2026-03-05,TRANSFER TO SAVINGS,500.00\n2026-03-06,ONLINE PAYMENT - THANK YOU,-500.00\n"
        "2026-03-07,STAPLES 0042,5.00\n",
    )
    assert [t.status for t in result.transactions[:2]] == [Status.EXCLUDED, Status.EXCLUDED]


def test_ids_follow_file_order_and_keep_the_source_line(classifier):
    result, _ = run(classifier, HEADER + "2026-03-05,STAPLES 0042,5.00\n2026-03-06,FIGMA,5.00\n")
    assert [t.id for t in result.transactions] == ["t-0001", "t-0002"]
    assert [t.line for t in result.transactions] == [2, 3]


# -- sign convention ---------------------------------------------------------------------------


def test_card_style_positive_purchases_are_detected(classifier):
    result, _ = run(
        classifier,
        HEADER
        + "2026-03-05,STAPLES 0042,50.00\n2026-03-06,FIGMA,10.00\n2026-03-07,ONLINE PAYMENT - THANK YOU,-60.00\n",
    )
    assert result.convention is Convention.POSITIVE_IS_SPENDING
    assert result.warnings == []
    assert result.transactions[0].spend_amount == Decimal("50.00")


def test_bank_style_negative_purchases_are_detected(classifier):
    result, _ = run(
        classifier,
        HEADER
        + "2026-03-05,STAPLES 0042,-50.00\n2026-03-06,FIGMA,-10.00\n2026-03-07,DEPOSIT CLIENT INVOICE 4,900.00\n",
    )
    assert result.convention is Convention.NEGATIVE_IS_SPENDING
    assert result.transactions[0].spend_amount == Decimal("50.00")
    assert result.transactions[2].spend_amount == Decimal("-900.00")
    assert result.transactions[2].amount == Decimal("900.00")  # original sign is preserved


def test_a_payment_line_overrules_a_misleading_majority(classifier):
    # Mostly-positive amounts, but the card payment is positive too: purchases must be negative.
    result, _ = run(
        classifier,
        HEADER
        + "2026-03-05,ONLINE PAYMENT - THANK YOU,100.00\n2026-03-06,PAYMENT RECEIVED THANK YOU,50.00\n"
        "2026-03-07,STAPLES 0042,-30.00\n",
    )
    assert result.convention is Convention.NEGATIVE_IS_SPENDING


def test_unclear_files_warn_that_the_convention_was_guessed(classifier):
    result, _ = run(classifier, HEADER + "2026-03-05,STAPLES 0042,50.00\n2026-03-06,FIGMA,10.00\n")
    assert result.convention is Convention.POSITIVE_IS_SPENDING
    assert any("guessed" in w for w in result.warnings)


@pytest.mark.parametrize("forced", list(Convention))
def test_a_manual_convention_always_wins(classifier, forced):
    result, _ = run(classifier, HEADER + "2026-03-05,STAPLES 0042,50.00\n", convention=forced)
    assert result.convention is forced
    expected = Decimal("50.00") if forced is Convention.POSITIVE_IS_SPENDING else Decimal("-50.00")
    assert result.transactions[0].spend_amount == expected


def test_debit_credit_columns_ignore_the_convention(classifier):
    result, _ = run(
        classifier,
        "Date,Description,Debit,Credit\n2026-03-05,STAPLES 0042,50.00,\n2026-03-06,DEPOSIT CLIENT INVOICE 4,,900.00\n",
        convention=Convention.NEGATIVE_IS_SPENDING,
    )
    assert result.transactions[0].spend_amount == Decimal("50.00")
    assert result.transactions[1].spend_amount == Decimal("-900.00")
