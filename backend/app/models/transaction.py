from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Category(str, Enum):
    SOFTWARE = "Software"
    TRAVEL = "Travel"
    MEALS = "Meals & Entertainment"
    OFFICE = "Office Supplies"
    UTILITIES = "Utilities"
    ADVERTISING = "Advertising & Marketing"
    FREELANCE = "Freelance Income"
    TRANSFER = "Transfer"
    REFUND = "Refund"
    NEEDS_REVIEW = "Needs Review"


class Transaction(BaseModel):
    id: int
    date: str
    description: str
    amount: float
    category: Category
    confidence: str  # "high", "low"
    is_debit: bool


class TransactionUpdate(BaseModel):
    category: Category


class StatementResult(BaseModel):
    transactions: list[Transaction]
    summary: dict[str, float]
    total_spending: float
    needs_review_count: int