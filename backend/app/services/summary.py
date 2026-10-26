from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.money import from_minor
from app.models import ParseErrorRow, Transaction
from app.schemas import (
    CategoryTotal,
    CountTotal,
    CurrencySummary,
    StatementSummary,
    TransferTotals,
    UnreviewedTotals,
)
from app.services.statements import get_statement


@dataclass
class _Bucket:
    count: int = 0
    minor: int = 0  # sum of signed amounts, in minor units

    def add(self, amount_minor: int) -> None:
        self.count += 1
        self.minor += amount_minor


@dataclass
class _Currency:
    expenses_by_category: dict[str, _Bucket] = field(default_factory=lambda: defaultdict(_Bucket))
    personal: _Bucket = field(default_factory=_Bucket)
    fees: _Bucket = field(default_factory=_Bucket)
    income: _Bucket = field(default_factory=_Bucket)
    refunds: _Bucket = field(default_factory=_Bucket)
    tax: _Bucket = field(default_factory=_Bucket)
    transfer_count: int = 0
    transfer_out: int = 0
    transfer_in: int = 0
    review_count: int = 0
    review_out: int = 0
    review_in: int = 0


def _money(minor: int) -> str:
    return str(from_minor(minor))


def _count_total(bucket: _Bucket, negate: bool = False) -> CountTotal:
    return CountTotal(count=bucket.count, total=_money(-bucket.minor if negate else bucket.minor))


def summary(db: Session, statement_id: int) -> StatementSummary:
    """Totals per currency. Currencies are never added together or converted.

    Sign convention: spending (expenses, fees, tax already paid) is reported as a positive
    amount; income and refunds are positive too. Rows still marked needs_review are kept out
    of every total except `needs_review`, so a total is never quietly wrong. Rows in category
    Personal go to `personal` (not deductible) whatever their kind, and never into expenses.
    Transfers are shown but are not spending."""
    get_statement(db, statement_id)
    rows = db.scalars(select(Transaction).where(Transaction.statement_id == statement_id))
    currencies: dict[str, _Currency] = defaultdict(_Currency)
    review_total = 0
    for t in rows:
        c = currencies[t.currency]
        if t.needs_review:
            review_total += 1
            c.review_count += 1
            if t.amount_minor < 0:
                c.review_out += -t.amount_minor
            else:
                c.review_in += t.amount_minor
        elif t.category == "Personal":
            c.personal.add(t.amount_minor)
        elif t.kind == "expense":
            c.expenses_by_category[t.category].add(t.amount_minor)
        elif t.kind == "fee":
            c.fees.add(t.amount_minor)
        elif t.kind == "income":
            c.income.add(t.amount_minor)
        elif t.kind == "refund":
            c.refunds.add(t.amount_minor)
        elif t.kind == "tax":
            c.tax.add(t.amount_minor)
        elif t.kind == "transfer":
            c.transfer_count += 1
            if t.amount_minor < 0:
                c.transfer_out += -t.amount_minor
            else:
                c.transfer_in += t.amount_minor

    out: dict[str, CurrencySummary] = {}
    for currency in sorted(currencies):
        c = currencies[currency]
        expenses = _Bucket(
            count=sum(b.count for b in c.expenses_by_category.values()),
            minor=sum(b.minor for b in c.expenses_by_category.values()),
        )
        out[currency] = CurrencySummary(
            expenses_by_category=[
                CategoryTotal(category=name, count=b.count, total=_money(-b.minor))
                for name, b in sorted(c.expenses_by_category.items())
            ],
            expenses=_count_total(expenses, negate=True),
            personal=_count_total(c.personal, negate=True),
            fees=_count_total(c.fees, negate=True),
            income=_count_total(c.income),
            refunds=_count_total(c.refunds),
            tax_already_paid=_count_total(c.tax, negate=True),
            transfers=TransferTotals(
                count=c.transfer_count,
                total_out=_money(c.transfer_out),
                total_in=_money(c.transfer_in),
            ),
            needs_review=UnreviewedTotals(
                count=c.review_count,
                total_out=_money(c.review_out),
                total_in=_money(c.review_in),
            ),
        )
    parse_errors = db.scalar(
        select(func.count()).select_from(ParseErrorRow).where(
            ParseErrorRow.statement_id == statement_id
        )
    )
    return StatementSummary(
        statement_id=statement_id,
        currencies=out,
        needs_review_count=review_total,
        parse_error_count=parse_errors or 0,
    )
