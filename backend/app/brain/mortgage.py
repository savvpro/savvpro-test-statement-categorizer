"""Split a mortgage payment into interest and principal.

Standard fixed-rate amortization, in exact Decimal arithmetic rounded to
cents. Nothing is guessed: if a payment does not match the schedule, a
LoanMismatchError explains why and the caller sends the row to review.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

from app.models import LoanDetails

CENT = Decimal("0.01")
TOLERANCE = Decimal("0.01")  # how far a real payment may differ from the schedule


class LoanMismatchError(ValueError):
    """The payment cannot be matched to the loan schedule."""


@dataclass(frozen=True)
class ScheduledPayment:
    number: int
    payment: Decimal
    interest: Decimal
    principal: Decimal
    balance_after: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_rate(loan: LoanDetails) -> Decimal:
    return loan.annual_rate_percent / Decimal(1200)


def monthly_payment(loan: LoanDetails) -> Decimal:
    """Level payment: P * r / (1 - (1 + r) ** -n)."""
    rate = monthly_rate(loan)
    if rate == 0:
        return _money(loan.original_principal / loan.term_months)
    factor = 1 - (1 + rate) ** -loan.term_months
    return _money(loan.original_principal * rate / factor)


@lru_cache(maxsize=32)
def build_schedule(loan: LoanDetails) -> tuple[ScheduledPayment, ...]:
    rate = monthly_rate(loan)
    level = monthly_payment(loan)
    balance = loan.original_principal
    schedule = []
    for number in range(1, loan.term_months + 1):
        interest = _money(balance * rate)
        if number == loan.term_months:
            principal = balance  # the last payment clears the rounding drift
            payment = principal + interest
        else:
            principal = level - interest
            payment = level
        balance -= principal
        schedule.append(ScheduledPayment(number, payment, interest, principal, balance))
    return tuple(schedule)


def payment_number_for(loan: LoanDetails, when) -> int:
    """Which payment is this? Counted by calendar month, so a payment made a
    few days early or late still lands on the right installment."""
    first = loan.first_payment_date
    return (when.year - first.year) * 12 + (when.month - first.month) + 1


def split_payment(loan: LoanDetails, when, paid: Decimal) -> ScheduledPayment:
    """Match a real payment (a positive amount) to the schedule."""
    number = payment_number_for(loan, when)
    if not 1 <= number <= loan.term_months:
        raise LoanMismatchError(
            f"A payment on {when.isoformat()} falls outside the loan schedule "
            f"(payments 1-{loan.term_months})."
        )
    scheduled = build_schedule(loan)[number - 1]
    if abs(paid - scheduled.payment) > TOLERANCE:
        raise LoanMismatchError(
            f"Paid {paid} but scheduled payment #{number} is {scheduled.payment}. "
            "It may include escrow or extra principal."
        )
    return scheduled