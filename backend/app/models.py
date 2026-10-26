"""Pydantic v2 models for the Statement Categorizer API."""

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    id: str
    date: str
    description: str
    amount: float = Field(..., description="Negative = spending, positive = money in")
    category: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    needs_review: bool
    is_duplicate: bool


class TransactionUpdate(BaseModel):
    category: str


class UploadResponse(BaseModel):
    transactions: list[Transaction]
    summary: dict[str, float]
    warnings: list[str]


class SummaryResponse(BaseModel):
    totals: dict[str, float]
    needs_review_total: float
    spending_total: float
