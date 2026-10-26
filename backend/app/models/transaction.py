"""
Transaction and tax categorization Pydantic models.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TransactionDirection(str, Enum):
    OUTFLOW = "OUTFLOW"
    INFLOW = "INFLOW"
    REFUND = "REFUND"
    TRANSFER = "TRANSFER"


class ReviewStatus(str, Enum):
    AUTO_VERIFIED = "AUTO_VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    MANUALLY_APPROVED = "MANUALLY_APPROVED"
    PERSONAL = "PERSONAL"


class TransactionRaw(BaseModel):
    id: str = Field(..., description="Unique transaction ID or row hash")
    date: str = Field(..., description="Transaction date in ISO format YYYY-MM-DD")
    raw_description: str = Field(..., description="Raw bank statement description")
    amount: float = Field(..., description="Raw transaction amount (positive or negative)")
    raw_type: Optional[str] = Field(None, description="Raw transaction type from bank if present")
    account: Optional[str] = Field(None, description="Account name or identifier if present")


class TransactionCategorized(BaseModel):
    id: str
    date: str
    raw_description: str
    clean_merchant: str
    amount: float = Field(..., description="Normalized transaction amount (absolute value)")
    direction: TransactionDirection
    category: str
    schedule_c_line: str
    tax_deductible: bool
    deductible_percentage: float = Field(..., description="Deductible percentage (0.0 to 1.0)")
    deductible_amount: float = Field(..., description="Calculated tax-deductible amount")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    status: ReviewStatus
    needs_review: bool
    review_reason: Optional[str] = None
    decision_rule: Optional[str] = None
    notes: Optional[str] = None


class CategorySummary(BaseModel):
    category: str
    schedule_c_line: str
    transaction_count: int
    gross_amount: float
    deductible_amount: float
    color: Optional[str] = None
    percentage: Optional[float] = 0.0


class TaxSummary(BaseModel):
    total_transactions: int
    gross_income: float
    total_expenses: float
    total_deductible_expenses: float
    net_taxable_profit: float
    estimated_tax_savings: float
    non_taxable_transfers: float
    needs_review_count: int
    needs_review_amount: float
    categories: List[CategorySummary]


class CategorizeResponse(BaseModel):
    filename: str
    parsed_count: int
    warnings: List[str] = []
    transactions: List[TransactionCategorized]
    summary: TaxSummary


class RecalculateRequest(BaseModel):
    transactions: List[TransactionCategorized]
