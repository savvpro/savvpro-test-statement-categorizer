"""Self Assessment estimate for a sole trader (England, Wales & NI rates).

Turns categorized rows into the numbers a freelancer actually cares about:
profit, income tax and Class 4 NIC. Assumes self-employment is the only
income. It is an estimate to plan with, not tax advice.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, List, Tuple

from pydantic import BaseModel

from ..domain.models import ALLOWABLE_EXPENSES, Category

ZERO = Decimal("0")


@dataclass(frozen=True)
class TaxYear:
    label: str
    personal_allowance: Decimal
    allowance_taper_start: Decimal
    bands: Tuple[Tuple[Decimal, Decimal], ...]  # (width of band in taxable income, rate); last width is open-ended
    class4_lower: Decimal
    class4_upper: Decimal
    class4_main_rate: Decimal
    class4_upper_rate: Decimal
    trading_allowance: Decimal


TAX_YEAR_2025_26 = TaxYear(
    label="2025/26",
    personal_allowance=Decimal("12570"),
    allowance_taper_start=Decimal("100000"),
    bands=((Decimal("37700"), Decimal("0.20")), (Decimal("87440"), Decimal("0.40")), (Decimal("Infinity"), Decimal("0.45"))),
    class4_lower=Decimal("12570"),
    class4_upper=Decimal("50270"),
    class4_main_rate=Decimal("0.06"),
    class4_upper_rate=Decimal("0.02"),
    trading_allowance=Decimal("1000"),
)


class TaxLine(BaseModel):
    category: Category
    amount: Decimal


class TaxEstimate(BaseModel):
    tax_year: str
    income: Decimal
    allowable_expenses: Decimal
    deduction_used: str
    deduction: Decimal
    profit: Decimal
    personal_allowance: Decimal
    income_tax: Decimal
    class4_nic: Decimal
    total_due: Decimal
    set_aside_rate: Decimal
    unresolved_rows: int
    notes: List[str]


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def estimate_tax(lines: Iterable[TaxLine], year: TaxYear = TAX_YEAR_2025_26) -> TaxEstimate:
    lines = list(lines)
    income = sum((l.amount for l in lines if l.category == Category.INCOME), ZERO)
    expenses = -sum((l.amount for l in lines if l.category in ALLOWABLE_EXPENSES), ZERO)
    expenses = max(expenses, ZERO)
    unresolved = sum(1 for l in lines if l.category == Category.NEEDS_REVIEW)

    # HMRC lets you claim the £1,000 trading allowance instead of actual expenses.
    use_allowance = expenses < year.trading_allowance
    deduction = min(year.trading_allowance, income) if use_allowance else expenses
    profit = max(income - deduction, ZERO)

    allowance = year.personal_allowance
    if profit > year.allowance_taper_start:
        allowance = max(ZERO, allowance - (profit - year.allowance_taper_start) / 2)

    taxable, income_tax = max(profit - allowance, ZERO), ZERO
    for width, rate in year.bands:
        portion = min(taxable, width)
        income_tax += portion * rate
        taxable -= portion
        if taxable <= 0:
            break

    class4 = ZERO
    if profit > year.class4_lower:
        class4 += (min(profit, year.class4_upper) - year.class4_lower) * year.class4_main_rate
    if profit > year.class4_upper:
        class4 += (profit - year.class4_upper) * year.class4_upper_rate

    total = income_tax + class4
    notes = ["Estimate only, assuming self-employment is your only income. Not tax advice."]
    if use_allowance and income > 0:
        notes.append("Your expenses are under £1,000, so the £1,000 trading allowance gives a bigger deduction.")
    if unresolved:
        notes.append(f"{unresolved} row(s) still need review, so these numbers may change.")

    return TaxEstimate(
        tax_year=year.label,
        income=_money(income),
        allowable_expenses=_money(expenses),
        deduction_used="trading allowance" if use_allowance else "actual expenses",
        deduction=_money(deduction),
        profit=_money(profit),
        personal_allowance=_money(allowance),
        income_tax=_money(income_tax),
        class4_nic=_money(class4),
        total_due=_money(total),
        set_aside_rate=(total / income).quantize(Decimal("0.001")) if income > 0 else ZERO,
        unresolved_rows=unresolved,
        notes=notes,
    )
