from decimal import Decimal

from app.domain.models import Category
from app.reporting.tax import TaxLine, estimate_tax


def lines(*pairs):
    return [TaxLine(category=c, amount=Decimal(a)) for c, a in pairs]


def test_profit_below_personal_allowance_has_no_tax():
    result = estimate_tax(lines((Category.INCOME, "10000"), (Category.SOFTWARE, "-2000")))
    assert result.profit == Decimal("8000.00") and result.total_due == 0


def test_basic_rate_tax_and_class4():
    result = estimate_tax(lines((Category.INCOME, "40000"), (Category.SOFTWARE, "-5000")))
    # profit 35,000; taxable 22,430 @20% = 4,486; class 4 = 22,430 @6% = 1,345.80
    assert result.income_tax == Decimal("4486.00")
    assert result.class4_nic == Decimal("1345.80")


def test_higher_rate_and_upper_class4():
    result = estimate_tax(lines((Category.INCOME, "61000"), (Category.SOFTWARE, "-1000")))
    # profit 60,000; taxable 47,430: 37,700 @20% + 9,730 @40% = 11,432; class 4: 37,700 @6% + 9,730 @2% = 2,456.60
    assert result.income_tax == Decimal("11432.00")
    assert result.class4_nic == Decimal("2456.60")


def test_personal_allowance_tapers_above_100k():
    assert estimate_tax(lines((Category.INCOME, "126140"), (Category.OFFICE, "-1000"))).personal_allowance == 0


def test_trading_allowance_used_when_expenses_are_small():
    result = estimate_tax(lines((Category.INCOME, "20000"), (Category.OFFICE, "-200")))
    assert result.deduction_used == "trading allowance" and result.deduction == Decimal("1000.00")


def test_non_business_rows_are_ignored_and_reviews_counted():
    result = estimate_tax(lines(
        (Category.INCOME, "20000"), (Category.SOFTWARE, "-3000"), (Category.PERSONAL, "-5000"),
        (Category.TRANSFER, "-1000"), (Category.TAX, "-2000"), (Category.NEEDS_REVIEW, "-50")))
    assert result.allowable_expenses == Decimal("3000.00")
    assert result.unresolved_rows == 1
