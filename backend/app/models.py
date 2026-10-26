from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Category(str, Enum):
    SOFTWARE = "Software"
    TRAVEL = "Travel"
    MEALS = "Meals"
    OFFICE_SUPPLIES = "Office Supplies"
    INCOME = "Income"
    REFUND = "Refund"
    TRANSFER = "Transfer"
    OTHER_BUSINESS_EXPENSE = "Other Business Expense"
    NEEDS_REVIEW = "Needs Review"


class TransactionStatus(str, Enum):
    CATEGORIZED = "categorized"
    NEEDS_REVIEW = "needs_review"
    MANUAL = "manual"


class Transaction(BaseModel):
    id: str = Field(..., description="Unique transaction ID")
    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    description: str = Field(..., description="Original transaction description")
    amount: float = Field(..., description="Normalized amount (negative for outflows/expenses, positive for inflows/income/refunds)")
    category: Category = Field(..., description="Assigned category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    status: TransactionStatus = Field(..., description="Status of categorization")
    matched_rule: str = Field(..., description="Human-readable explanation of why this category was assigned")
    is_reviewed: bool = Field(default=False, description="Whether the category has been manually set or confirmed")


class TransactionUpdateRequest(BaseModel):
    category: Category = Field(..., description="New category to set")


class CategorySummary(BaseModel):
    category: Category
    count: int
    total_amount: float
    percentage: float = 0.0


class StatementSummary(BaseModel):
    total_transactions: int
    total_income: float
    total_expenses: float
    total_refunds: float
    net_expenses: float
    net_cashflow: float
    transfers_count: int
    transfers_total: float
    needs_review_count: int
    category_breakdown: List[CategorySummary]


class UploadResponse(BaseModel):
    statement_id: str
    filename: str
    transactions: List[Transaction]
    summary: StatementSummary
    warnings: List[str] = []
