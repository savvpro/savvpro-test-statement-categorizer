from __future__ import annotations

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: str
    label: str
    kind: str
    schedule_c_line: str | None
    description: str


class TransactionOut(BaseModel):
    id: int
    line: int
    date: str
    description: str
    merchant: str
    amount_cents: int = Field(description="Signed: positive = money in, negative = money out")
    direction: str
    bank_category: str | None
    category: str | None
    status: str = Field(description="auto | needs_review | reviewed")
    confidence: float
    source: str
    reasons: list[str]
    suggestions: list[str]
    flags: list[str]
    engine_category: str | None


class SkippedRowOut(BaseModel):
    line: int
    reason: str
    content: str


class CategoryTotal(BaseModel):
    category: str
    label: str
    kind: str
    schedule_c_line: str | None
    total_cents: int = Field(description="Income: money in. Expenses: net spend after refunds.")
    count: int
    refund_cents: int


class Summary(BaseModel):
    income_cents: int
    deductible_expenses_cents: int
    net_profit_cents: int
    personal_cents: int
    transfers_in_cents: int
    transfers_out_cents: int
    needs_review_count: int
    needs_review_cents: int
    auto_count: int
    reviewed_count: int
    categories: list[CategoryTotal]


class StatementListItem(BaseModel):
    id: int
    filename: str
    uploaded_at: str
    transaction_count: int
    needs_review_count: int
    period_start: str | None
    period_end: str | None


class StatementOut(StatementListItem):
    file_format: str
    sign_convention: str
    warnings: list[str]
    skipped: list[SkippedRowOut]
    transactions: list[TransactionOut]
    summary: Summary


class TransactionUpdate(BaseModel):
    category: str | None = Field(description="Category id, or null to send the row back to review")
    remember: bool = Field(
        default=True, description="Learn this choice for the merchant and re-apply it"
    )


class RuleOut(BaseModel):
    merchant_key: str
    direction: str
    category: str
    example: str
    updated_at: str


class SampleOut(BaseModel):
    name: str
    title: str
    description: str
