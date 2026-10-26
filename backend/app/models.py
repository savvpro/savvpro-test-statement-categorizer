from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, PlainSerializer

Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

Kind = Literal["expense", "personal", "refund", "income", "transfer", "review"]


class RawTransaction(BaseModel):
    """A row as read from the statement. `amount` is signed: negative = money out."""

    line: int
    date: date
    description: str
    amount: Money


class CategorizedTransaction(BaseModel):
    id: int
    date: date
    description: str
    amount: Money
    merchant_key: str
    category: str
    suggested_category: str | None = None
    kind: Kind
    confidence: float
    reason: str
    needs_review: bool


class ParseIssue(BaseModel):
    line: int
    message: str


class CategoryTotal(BaseModel):
    category: str
    count: int
    total: Money


class Summary(BaseModel):
    expense_categories: list[CategoryTotal]
    business_expenses: Money
    personal_spending: Money
    income: Money
    transfers_excluded: Money
    needs_review_count: int
    needs_review_amount: Money


class CategorizeResponse(BaseModel):
    transactions: list[CategorizedTransaction]
    summary: Summary
    issues: list[ParseIssue]
    warnings: list[str]
    categories: list[str]
