"""Domain models shared across ingestion, categorization, reporting and the API."""
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Category(str, Enum):
    """Categories aligned with HMRC Self Assessment (SA103) groupings."""

    INCOME = "Business Income"
    SOFTWARE = "Phone, Internet & Software"
    OFFICE = "Office Costs"
    TRAVEL = "Travel"
    PROFESSIONAL = "Professional Fees"
    ADVERTISING = "Advertising & Marketing"
    TRAINING = "Training"
    BANK_CHARGES = "Bank & Finance Charges"
    TAX = "Tax Payments"
    REFUND = "Refund"
    TRANSFER = "Transfer (Not Spending)"
    PERSONAL = "Personal (Not Allowable)"
    NEEDS_REVIEW = "Needs Review"


ALLOWABLE_EXPENSES = frozenset({
    Category.SOFTWARE, Category.OFFICE, Category.TRAVEL, Category.PROFESSIONAL,
    Category.ADVERTISING, Category.TRAINING, Category.BANK_CHARGES,
})
# Categories that make sense regardless of whether money went in or out.
DIRECTION_NEUTRAL = frozenset({Category.TRANSFER, Category.PERSONAL, Category.NEEDS_REVIEW})


def fits_direction(category: Category, amount: Decimal) -> bool:
    """Whether a category is plausible for money in (amount > 0) or money out."""
    if category in DIRECTION_NEUTRAL:
        return True
    if amount > 0:
        return category in (Category.INCOME, Category.REFUND)
    return category not in (Category.INCOME, Category.REFUND)


class RawTransaction(BaseModel):
    """A row as read from the statement, before any categorization."""

    row: int
    date: date
    description: str
    amount: Decimal  # negative = money out, positive = money in


class CategorizedTransaction(RawTransaction):
    merchant: str
    category: Category
    confidence: float
    reasons: List[str]
    flags: List[str] = []
    suggestion: Optional[Category] = None  # best guess shown when the engine is unsure
    refund_of: Optional[int] = None  # row number of the original purchase


class ParseIssue(BaseModel):
    row: int
    message: str


class ParsedStatement(BaseModel):
    transactions: List[RawTransaction]
    issues: List[ParseIssue]


class CategoryTotal(BaseModel):
    category: Category
    total: Decimal
    count: int


class CategorizationResult(BaseModel):
    transactions: List[CategorizedTransaction]
    issues: List[ParseIssue]
    totals: List[CategoryTotal]
    needs_review: int
