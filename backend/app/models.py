from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Category(str, Enum):
    SOFTWARE = "Software & Subscriptions"
    TRAVEL = "Travel & Transportation"
    MEALS = "Meals & Entertainment"
    OFFICE = "Office Supplies"
    PROFESSIONAL = "Professional Services"
    MARKETING = "Marketing & Advertising"
    EQUIPMENT = "Equipment & Hardware"
    UTILITIES = "Utilities & Internet"
    NOT_SPENDING = "Transfer / Not Spending"
    REFUND = "Refund"
    NEEDS_REVIEW = "Needs Review"


Confidence = Literal["high", "medium", "low", "unknown"]


class Transaction(BaseModel):
    id: str
    date: str
    description: str
    amount: float
    raw_amount: str = ""


class CategorizedTransaction(Transaction):
    category: Category
    confidence: Confidence
    reason: str
    user_category: Category | None = None

    @property
    def effective_category(self) -> Category:
        return self.user_category or self.category


class CategorySummary(BaseModel):
    category: Category
    total: float
    count: int


class CategorizeResponse(BaseModel):
    transactions: list[CategorizedTransaction]
    summaries: list[CategorySummary]
    needs_review_count: int


class UpdateCategoryRequest(BaseModel):
    transaction_id: str
    category: Category


class CategoriesResponse(BaseModel):
    categories: list[str]
