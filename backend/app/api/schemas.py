"""API contract (01-architecture section 6). snake_case JSON. Changes need orchestrator approval."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AccountType,
    Category,
    CategoryKind,
    Direction,
    SourceFormat,
    Status,
)


class ParseWarningOut(BaseModel):
    code: str
    message: str
    row_index: int | None = None


class StatementCounts(BaseModel):
    auto: int
    needs_review: int
    user_confirmed: int
    duplicate: int


class StatementOut(BaseModel):
    id: str
    filename: str
    source_format: SourceFormat
    account_type: AccountType
    uploaded_at: datetime
    period_start: date | None
    period_end: date | None
    row_count: int
    counts: StatementCounts
    warnings: list[ParseWarningOut]


class TransactionOut(BaseModel):
    id: str
    row_index: int
    posted_date: date
    amount_cents: int
    direction: Direction
    description: str
    memo: str | None
    merchant_key: str
    category: Category | None
    brain_category: Category | None
    status: Status
    confidence: float
    reasons: list[str]
    flags: list[str]
    is_refund: bool
    duplicate_of_id: str | None
    similar_count: int


class TransactionListOut(BaseModel):
    items: list[TransactionOut]
    total: int


class TransactionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    remember: bool = False
    apply_to_similar: bool = False


class PatchResult(BaseModel):
    updated: list[TransactionOut]
    rule_created: bool


class ScheduleELine(BaseModel):
    line: str
    label: str
    category: Category
    total_cents: int


class Unresolved(BaseModel):
    count: int
    total_abs_cents: int


class DuplicatesOut(BaseModel):
    count: int


class SummaryOut(BaseModel):
    income: dict[str, int]
    expenses: dict[str, int]
    schedule_e: list[ScheduleELine]
    total_income_cents: int
    total_expense_cents: int = Field(description="Signed sum of expense categories (<= 0).")
    net_cents: int
    excluded: dict[str, int]
    unresolved: Unresolved
    duplicates: DuplicatesOut


class CategoryOut(BaseModel):
    code: Category
    label: str
    kind: CategoryKind
    schedule_e_line: str | None
    allowed_directions: list[Direction]


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str | None = None
    errors: list[dict[str, object]] | None = None
    existing_id: str | None = Field(
        default=None, description="Present on 409: id of the statement with identical content."
    )


class HealthOut(BaseModel):
    status: Literal["ok", "ready", "not_ready"]
