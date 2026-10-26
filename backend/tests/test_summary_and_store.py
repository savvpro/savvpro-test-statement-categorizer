from datetime import date
from decimal import Decimal

from app.categories import Category as C
from app.models import Statement, Transaction
from app.services.summary import summarize
from app.store import StatementStore


def txn(amount, category, related=None, row=2):
    return Transaction(
        row=row,
        date=date(2026, 10, 1),
        description="X",
        amount=Decimal(str(amount)),
        category=category,
        related_category=related,
    )


def test_tax_summary_nets_refunds_against_the_expense_they_reverse():
    rows = [
        txn(45000, C.INCOME),
        txn(-6500, C.FUEL),
        txn(-850, C.TOLLS_PARKING),
        txn(6500, C.REFUND, related=C.FUEL),  # fuel refunded in full
        txn(-1450, C.PERSONAL),
        txn(-10000, C.TRANSFER),
        txn(-3000, C.NEEDS_REVIEW),
        txn(900, C.NEEDS_REVIEW),
    ]
    tax = summarize(rows).tax
    assert tax.income == Decimal("45000")
    assert tax.deductible_expenses == Decimal("850")  # 6500 + 850 - 6500
    assert tax.refunds_netted == Decimal("6500")
    assert tax.personal_spending == Decimal("1450")
    assert tax.not_spending == Decimal("-10000")
    assert tax.estimated_profit == Decimal("44150")
    assert (tax.needs_review_count, tax.needs_review_out, tax.needs_review_in) == (
        2,
        Decimal("3000"),
        Decimal("900"),
    )
    assert tax.complete is False


def test_refund_that_cannot_be_tied_to_an_expense_is_kept_separate_and_never_income():
    tax = summarize([txn(45000, C.INCOME), txn(500, C.REFUND, related=None)]).tax
    assert tax.income == Decimal("45000")
    assert tax.other_refunds == Decimal("500")
    assert tax.deductible_expenses == 0


def test_refund_of_a_personal_purchase_does_not_reduce_deductions():
    tax = summarize([txn(-6500, C.FUEL), txn(300, C.REFUND, related=C.PERSONAL)]).tax
    assert tax.deductible_expenses == Decimal("6500")
    assert tax.other_refunds == Decimal("300")


def test_complete_when_nothing_needs_review():
    assert summarize([txn(10, C.INCOME)]).tax.complete is True


def test_by_category_is_in_a_fixed_order_and_signed():
    summary = summarize([txn(-5, C.PERSONAL), txn(-6, C.FUEL), txn(-7, C.FUEL)])
    assert [c.category for c in summary.by_category] == [C.FUEL, C.PERSONAL]
    assert summary.by_category[0].total == Decimal("-13")
    assert summary.by_category[0].count == 2


def test_money_is_exact_not_floating_point():
    rows = [txn("0.10", C.INCOME), txn("0.20", C.INCOME)]
    assert summarize(rows).tax.income == Decimal("0.30")


def test_empty_statement():
    summary = summarize([])
    assert summary.total_transactions == 0
    assert summary.tax.complete is True


def test_store_drops_the_oldest_statement_beyond_its_limit():
    store = StatementStore(max_statements=2)
    statements = [Statement(filename=f"{i}.csv", transactions=[]) for i in range(3)]
    for s in statements:
        store.add(s)
    assert store.get(statements[0].id) is None
    assert store.get(statements[1].id) is statements[1]
    assert len(store) == 2
