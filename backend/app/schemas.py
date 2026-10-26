from datetime import UTC, date, datetime

from pydantic import BaseModel, field_validator

from app.core.domain import NEEDS_REVIEW, Category, Kind
from app.core.money import from_minor
from app.models import ParseErrorRow, Statement, Transaction


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class TransactionOut(BaseModel):
    id: int
    row_number: int
    date: date
    raw_description: str
    merchant_key: str
    amount: str  # signed decimal string, e.g. "-1850.00". Never a float
    currency: str
    category: str
    kind: str
    confidence: float
    rule_id: str | None
    reason: str
    needs_review: bool
    suggested_category: str | None
    edited_by_user: bool

    @classmethod
    def from_row(cls, t: Transaction) -> "TransactionOut":
        return cls(
            id=t.id,
            row_number=t.row_number,
            date=t.date,
            raw_description=t.raw_description,
            merchant_key=t.merchant_key,
            amount=str(from_minor(t.amount_minor)),
            currency=t.currency,
            category=t.category,
            kind=t.kind,
            confidence=t.confidence,
            rule_id=t.rule_id,
            reason=t.reason,
            needs_review=t.needs_review,
            suggested_category=t.suggested_category,
            edited_by_user=t.edited_by_user,
        )


class ParseErrorOut(BaseModel):
    row_number: int
    raw_line: str
    reason: str

    @classmethod
    def from_row(cls, e: ParseErrorRow) -> "ParseErrorOut":
        return cls(row_number=e.row_number, raw_line=e.raw_line, reason=e.reason)


class StatementOut(BaseModel):
    id: int
    filename: str
    profile_name: str
    account_type: str
    uploaded_at: datetime
    skipped_count: int  # blank lines that were ignored
    row_count: int
    parse_error_count: int
    needs_review_count: int

    @classmethod
    def from_row(
        cls, s: Statement, row_count: int, parse_error_count: int, needs_review_count: int
    ) -> "StatementOut":
        return cls(
            id=s.id,
            filename=s.filename,
            profile_name=s.profile_name,
            account_type=s.account_type,
            uploaded_at=_utc(s.uploaded_at),
            skipped_count=s.skipped_count,
            row_count=row_count,
            parse_error_count=parse_error_count,
            needs_review_count=needs_review_count,
        )


class StatementDetail(StatementOut):
    transactions: list[TransactionOut]
    parse_errors: list[ParseErrorOut]


class CorrectionIn(BaseModel):
    category: Category
    kind: Kind | None = None
    remember: bool = False

    @field_validator("category")
    @classmethod
    def _not_needs_review(cls, value: str) -> str:
        if value == NEEDS_REVIEW:
            raise ValueError("pick a real category: a fixed row cannot stay in Needs Review")
        return value


class CorrectionOut(BaseModel):
    transaction: TransactionOut
    reclassified_count: int  # other rows changed because of "remember"


class CategoriesOut(BaseModel):
    categories: list[str]
    kinds: list[str]


class CountTotal(BaseModel):
    count: int
    total: str


class CategoryTotal(BaseModel):
    category: str
    count: int
    total: str


class TransferTotals(BaseModel):
    count: int
    total_out: str
    total_in: str


class UnreviewedTotals(BaseModel):
    count: int
    total_out: str
    total_in: str


class CurrencySummary(BaseModel):
    expenses_by_category: list[CategoryTotal]
    expenses: CountTotal
    personal: CountTotal  # category Personal: not deductible, so not in expenses
    fees: CountTotal
    income: CountTotal
    refunds: CountTotal
    tax_already_paid: CountTotal
    transfers: TransferTotals
    needs_review: UnreviewedTotals


class StatementSummary(BaseModel):
    statement_id: int
    currencies: dict[str, CurrencySummary]
    needs_review_count: int
    parse_error_count: int
