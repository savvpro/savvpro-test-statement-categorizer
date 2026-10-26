"""Response and request models for the HTTP API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import Category, Statement, Transaction
from app.summary import Summary, summarize

CategoryKindName = Literal["expense", "non_spending", "income", "review"]


class CategoryOut(BaseModel):
    id: str
    name: str
    kind: CategoryKindName
    deductible: Literal["full", "partial", "none"] | None

    @classmethod
    def from_domain(cls, c: Category) -> CategoryOut:
        return cls(id=c.id, name=c.name, kind=c.kind.value, deductible=c.deductible)


class ConfigOut(BaseModel):
    max_upload_mb: int
    accepted_extensions: list[str]
    max_rows: int
    max_pdf_pages: int


class TransactionOut(BaseModel):
    id: str
    line: int
    date: date
    description: str
    merchant: str
    amount: float
    spend_amount: float
    currency: str
    category_id: str
    category_name: str
    kind: CategoryKindName
    status: Literal["categorized", "needs_review", "excluded", "user_corrected"]
    confidence: float
    reasons: list[str]
    flags: list[str]
    refund_of: str | None
    suggestions: list[str]

    @classmethod
    def from_domain(cls, t: Transaction) -> TransactionOut:
        return cls(
            id=t.id,
            line=t.line,
            date=t.date,
            description=t.description,
            merchant=t.merchant,
            amount=float(t.amount),
            spend_amount=float(t.spend_amount),
            currency=t.currency,
            category_id=t.category_id,
            category_name=t.category_name,
            kind=t.kind.value,
            status=t.status.value,
            confidence=t.confidence,
            reasons=list(t.reasons),
            flags=[f.value for f in t.flags],
            refund_of=t.refund_of,
            suggestions=list(t.suggestions),
        )


class CategoryTotalOut(BaseModel):
    category_id: str
    category_name: str
    kind: CategoryKindName
    count: int
    total: float


class SummaryOut(BaseModel):
    totals: list[CategoryTotalOut]
    total_spending: float
    total_refunds: float
    net_spending: float
    excluded_total: float
    income_total: float
    needs_review_count: int
    transaction_count: int

    @classmethod
    def from_domain(cls, s: Summary) -> SummaryOut:
        return cls(
            totals=[
                CategoryTotalOut(
                    category_id=c.category_id,
                    category_name=c.category_name,
                    kind=c.kind.value,
                    count=c.count,
                    total=float(c.total),
                )
                for c in s.totals
            ],
            total_spending=float(s.total_spending),
            total_refunds=float(s.total_refunds),
            net_spending=float(s.net_spending),
            excluded_total=float(s.excluded_total),
            income_total=float(s.income_total),
            needs_review_count=s.needs_review_count,
            transaction_count=s.transaction_count,
        )


class RejectedRowOut(BaseModel):
    line: int
    raw: str
    reason: str


class StatementOut(BaseModel):
    id: str
    filename: str
    currency: str
    created_at: datetime
    source_format: Literal["csv", "xlsx", "pdf", "ofx", "camt053", "mt940"]
    convention: Literal["negative_is_spending", "positive_is_spending"]
    transactions: list[TransactionOut]
    rejected_rows: list[RejectedRowOut]
    warnings: list[str]
    summary: SummaryOut

    @classmethod
    def from_domain(cls, s: Statement) -> StatementOut:
        return cls(
            id=s.id,
            filename=s.filename,
            currency=s.currency,
            created_at=s.created_at,
            source_format=s.source_format.value,
            convention=s.convention.value,
            transactions=[TransactionOut.from_domain(t) for t in s.transactions],
            rejected_rows=[
                RejectedRowOut(line=r.line, raw=r.raw, reason=r.reason) for r in s.rejected_rows
            ],
            warnings=list(s.warnings),
            summary=SummaryOut.from_domain(summarize(s.transactions)),
        )


class CorrectionIn(BaseModel):
    category_id: str = Field(min_length=1, max_length=64)
    apply_to_similar: bool = False


class CorrectionOut(BaseModel):
    statement: StatementOut
    updated_count: int
