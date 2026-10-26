"""Database tables (SQLModel) and API response schemas (pydantic)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from app.engine.categories import NOT_SPENDING_CATEGORIES


def utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


# --------------------------------------------------------------------------- tables


class Statement(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    uploaded_at: datetime = Field(default_factory=utcnow)
    row_count: int = 0
    warnings_json: str = "[]"

    @property
    def warnings(self) -> list[str]:
        return json.loads(self.warnings_json)


class Transaction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    statement_id: int = Field(foreign_key="statement.id", index=True)
    row_number: int
    date: date
    description: str
    normalized_merchant: str = Field(index=True)
    amount: float
    currency: str = "USD"
    category: str
    confidence: float
    reason: str
    needs_review: bool = False
    is_duplicate: bool = False
    source: str = "rule"
    notes_json: str = "[]"

    @property
    def notes(self) -> list[str]:
        return json.loads(self.notes_json)

    @property
    def status(self) -> str:
        if self.is_duplicate:
            return "duplicate"
        if self.needs_review:
            return "needs_review"
        if self.category in NOT_SPENDING_CATEGORIES:
            return "not_spending"
        if self.source == "user":
            return "user"
        if self.source == "learned":
            return "learned"
        return "auto"


class LearnedRule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    merchant: str = Field(unique=True, index=True)
    category: str
    created_at: datetime = Field(default_factory=utcnow)
    times_applied: int = 0


# --------------------------------------------------------------------------- API schemas


class TransactionOut(BaseModel):
    id: int
    statement_id: int
    row_number: int
    date: date
    description: str
    normalized_merchant: str
    amount: float
    currency: str
    category: str
    confidence: float
    reason: str
    needs_review: bool
    is_duplicate: bool
    source: str
    status: str
    notes: list[str]

    @classmethod
    def from_row(cls, row: Transaction) -> TransactionOut:
        return cls(
            **row.model_dump(exclude={"notes_json"}),
            status=row.status,
            notes=row.notes,
        )


class StatementOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    row_count: int
    warnings: list[str]
    transactions: list[TransactionOut]


class StatementListItem(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    row_count: int
    needs_review_count: int


class CategoryTotal(BaseModel):
    category: str
    kind: str
    total: float
    count: int


class Totals(BaseModel):
    transactions: int
    auto_categorized: int
    needs_review: int
    duplicates: int
    spending: float
    refunds: float
    net_spending: float
    income: float
    not_spending: float


class Summary(BaseModel):
    statement_id: int
    totals: Totals
    categories: list[CategoryTotal]


class LearnedRuleOut(BaseModel):
    id: int
    merchant: str
    category: str
    created_at: datetime
    times_applied: int


class CategoryUpdate(BaseModel):
    category: str


class TransactionUpdateResult(BaseModel):
    transaction: TransactionOut
    learned_rule: LearnedRuleOut | None
    also_updated: list[int]
