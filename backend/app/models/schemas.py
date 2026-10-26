from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    DEBIT = "DEBIT"      # Outflow / Expense
    CREDIT = "CREDIT"    # Inflow / Income or Refund


class CategoryName(str, Enum):
    SOFTWARE_SUBSCRIPTIONS = "Software & Subscriptions"
    OFFICE_EQUIPMENT = "Office & Equipment"
    TRAVEL_RIDESHARE = "Travel & Rideshare"
    MEALS_ENTERTAINMENT = "Meals & Entertainment"
    MARKETING_ADVERTISING = "Marketing & Advertising"
    PROFESSIONAL_FEES = "Professional & Banking Fees"
    UTILITIES_INTERNET = "Utilities & Internet"
    GROSS_INCOME = "Gross Income"
    INTERNAL_TRANSFER = "Internal Transfer / Owner Draw"
    REFUND_CREDIT = "Refund / Expense Offset"
    NEEDS_REVIEW = "Needs Review"


class TaxDeductibility(str, Enum):
    FULLY_DEDUCTIBLE = "100% Deductible"
    PARTIALLY_DEDUCTIBLE = "50% Deductible (Meals)"
    NON_DEDUCTIBLE = "Non-Deductible / Transfer"
    TAXABLE_INCOME = "Taxable Gross Income"
    EXPENSE_OFFSET = "Expense Offset (Credit)"
    PENDING_REVIEW = "Pending User Review"


class Transaction(BaseModel):
    id: str = Field(..., description="Unique transaction ID")
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    raw_description: str = Field(..., description="Original statement line text")
    clean_merchant: str = Field(..., description="Normalized merchant name")
    amount: float = Field(..., description="Transaction amount (positive = debit/expense, negative = credit/refund/income)")
    transaction_type: TransactionType = Field(..., description="DEBIT or CREDIT")
    category: CategoryName = Field(..., description="Assigned category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Brain confidence score between 0.0 and 1.0")
    needs_review: bool = Field(..., description="Whether user verification is required")
    review_reason: Optional[str] = Field(None, description="Explanation if marked for review or rule explanation")
    tax_status: TaxDeductibility = Field(..., description="Tax deductibility classification")
    user_edited: bool = Field(False, description="Flag indicating if user modified the category")


class CategorySummary(BaseModel):
    category: CategoryName
    total_amount: float
    count: int
    tax_status: TaxDeductibility
    percentage_of_expenses: float


class StatementSummary(BaseModel):
    total_transactions: int
    total_income: float
    total_expenses: float
    net_tax_deductible_expenses: float
    total_refunds: float
    transfers_excluded: float
    needs_review_count: int
    accuracy_rate: float
    categories: List[CategorySummary]


class StatementAnalysisResponse(BaseModel):
    filename: str
    summary: StatementSummary
    transactions: List[Transaction]


class UpdateCategoryRequest(BaseModel):
    transaction_id: str
    new_category: CategoryName
    apply_to_future: bool = True


class RuleDefinition(BaseModel):
    canonical_merchant: str
    category: CategoryName
    tax_status: TaxDeductibility
    keywords: List[str]
    notes: Optional[str] = None
