import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.brain.categorizer import Categorizer
from app.brain.mortgage import (
    LoanMismatchError,
    build_schedule,
    monthly_payment,
    payment_number_for,
    split_payment,
)
from app.models import Category, LoanDetails, RawTransaction
from app.parsing.csv_parser import parse_statement

DATA = Path(__file__).parent.parent / "data"


def make_loan(**overrides) -> LoanDetails:
    values = dict(
        original_principal=Decimal("200000"),
        annual_rate_percent=Decimal("6"),
        term_months=360,
        first_payment_date=dt.date(2025, 1, 1),
    )
    values.update(overrides)
    return LoanDetails(**values)


def payment_tx(day: dt.date, amount: str, row: int = 2) -> RawTransaction:
    return RawTransaction(
        row_number=row, date=day, description="WELLS FARGO HOME MTG PYMT",
        amount=Decimal(amount),
    )


# ------------------------------------------------------------ the math
def test_monthly_payment_matches_known_value():
    assert monthly_payment(make_loan()) == Decimal("1199.10")


def test_first_payment_split():
    first = build_schedule(make_loan())[0]
    assert first.interest == Decimal("1000.00")
    assert first.principal == Decimal("199.10")


def test_every_payment_adds_up_and_loan_ends_at_zero():
    schedule = build_schedule(make_loan())
    assert all(p.interest + p.principal == p.payment for p in schedule)
    assert schedule[-1].balance_after == Decimal("0.00")
    assert sum(p.principal for p in schedule) == Decimal("200000.00")


def test_interest_shrinks_and_principal_grows_over_time():
    schedule = build_schedule(make_loan())
    assert schedule[0].interest > schedule[100].interest > schedule[-1].interest
    assert schedule[0].principal < schedule[100].principal


def test_zero_interest_loan():
    loan = make_loan(annual_rate_percent=Decimal("0"), term_months=100,
                     original_principal=Decimal("10000"))
    first = build_schedule(loan)[0]
    assert first.interest == Decimal("0.00") and first.payment == Decimal("100.00")


def test_payment_number_counts_calendar_months():
    loan = make_loan()
    assert payment_number_for(loan, dt.date(2025, 1, 28)) == 1
    assert payment_number_for(loan, dt.date(2025, 12, 3)) == 12
    assert payment_number_for(loan, dt.date(2026, 1, 3)) == 13


@pytest.mark.parametrize(
    "bad", [dict(original_principal=Decimal("-5")), dict(term_months=0),
            dict(annual_rate_percent=Decimal("-1"))]
)
def test_invalid_loan_details_are_rejected(bad):
    with pytest.raises(ValidationError):
        make_loan(**bad)


# ----------------------------------------------- matching real payments
def test_payment_that_does_not_match_the_schedule_is_rejected():
    with pytest.raises(LoanMismatchError, match="escrow"):
        split_payment(make_loan(), dt.date(2025, 3, 3), Decimal("1500.00"))


def test_payment_outside_the_schedule_is_rejected():
    with pytest.raises(LoanMismatchError, match="outside"):
        split_payment(make_loan(), dt.date(2024, 6, 1), Decimal("1199.10"))


# ------------------------------------------------ inside the categorizer
def test_mortgage_payment_is_split_when_loan_details_exist():
    brain = Categorizer(loan=make_loan())
    [row] = brain.categorize_all([payment_tx(dt.date(2025, 1, 3), "-1199.10")])
    assert row.category == Category.MORTGAGE_PAYMENT
    assert [s.category for s in row.splits] == [
        Category.MORTGAGE_INTEREST, Category.MORTGAGE_PRINCIPAL
    ]
    assert row.splits[0].amount == Decimal("-1000.00")
    assert sum(s.amount for s in row.splits) == row.amount
    assert not row.needs_review


def test_mortgage_without_loan_details_still_needs_review():
    [row] = Categorizer().categorize_all([payment_tx(dt.date(2025, 1, 3), "-1199.10")])
    assert row.needs_review and row.splits == []


def test_mortgage_amount_mismatch_goes_to_review_not_guessed():
    brain = Categorizer(loan=make_loan())
    [row] = brain.categorize_all([payment_tx(dt.date(2025, 1, 3), "-1450.00")])
    assert row.needs_review
    assert "could not be split" in row.explanation and row.splits == []


def test_two_payments_in_one_month_second_goes_to_review():
    brain = Categorizer(loan=make_loan())
    first, second = brain.categorize_all(
        [payment_tx(dt.date(2025, 1, 3), "-1199.10", row=2),
         payment_tx(dt.date(2025, 1, 20), "-1199.10", row=3)]
    )
    assert first.category == Category.MORTGAGE_PAYMENT
    assert second.needs_review and "already matched" in second.explanation


def test_sample_statement_mortgage_rows_all_split():
    loan = make_loan()
    parsed = parse_statement((DATA / "bank_a.csv").read_bytes())
    results = Categorizer(loan=loan).categorize_all(parsed.transactions)

    mortgage = [t for t in results if "MTG" in t.normalized]
    assert len(mortgage) == 12
    assert all(t.category == Category.MORTGAGE_PAYMENT for t in mortgage)
    assert all(sum(s.amount for s in t.splits) == t.amount for t in mortgage)

    interest = [-t.splits[0].amount for t in mortgage]
    assert interest == sorted(interest, reverse=True)  # interest only falls
    # Non-mortgage rows are unaffected.
    assert all(t.splits == [] for t in results if "MTG" not in t.normalized)