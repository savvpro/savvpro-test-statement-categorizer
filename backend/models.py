"""
Pydantic models for the Statement Categorizer.

All monetary values use Decimal for precision and validate finiteness.
"""

from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import date


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransactionType(str, Enum):
    """How the transaction affects the books – independent of business category."""
    INCOME = "income"
    EXPENSE = "expense"
    REFUND = "refund"
    TRANSFER = "transfer"
    FEE = "fee"
    UNKNOWN = "unknown"


class BusinessCategory(str, Enum):
    """What the transaction relates to in the business."""
    SOFTWARE = "Software"
    ADVERTISING = "Advertising"
    OFFICE_SUPPLIES = "Office Supplies"
    TRAVEL = "Travel"
    ACCOMMODATION = "Accommodation"
    BANK_FEES = "Bank Fees"
    MEALS = "Meals & Entertainment"
    CLIENT_INCOME = "Client Income"
    PAYMENT_PROCESSING = "Payment Processing"
    INTERNAL_TRANSFER = "Internal Transfer"
    CASH_WITHDRAWAL = "Cash Withdrawal"
    CONTRACTOR_EXPENSE = "Contractor Expense"
    GENERAL_EXPENSE = "General Expense"
    UNKNOWN = "Unknown"


class ReviewStatus(str, Enum):
    AUTO_CATEGORIZED = "auto"
    NEEDS_REVIEW = "needs_review"
    USER_CONFIRMED = "user_confirmed"
    USER_CORRECTED = "user_corrected"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

class RawTransaction(BaseModel):
    """A single row parsed from the CSV before categorization."""
    date: date
    description: str
    amount: Decimal = Field(ge=Decimal("-999999999999.99"), le=Decimal("999999999999.99"), decimal_places=2)

    @field_validator("amount")
    @classmethod
    def validate_finite_amount(cls, v: Decimal) -> Decimal:
        if not v.is_finite() or v.is_nan():
            raise ValueError("Amount must be a finite numerical value.")
        return v


class CategorizedTransaction(BaseModel):
    """A fully categorized transaction with audit trail."""
    id: int
    date: date
    description: str
    amount: Decimal = Field(ge=Decimal("-999999999999.99"), le=Decimal("999999999999.99"), decimal_places=2)
    transaction_type: TransactionType
    business_category: BusinessCategory
    review_status: ReviewStatus
    confidence: Confidence
    explanation: str
    rule_id: str
    is_possible_duplicate: bool = False
    duplicate_group_id: Optional[int] = None
    linked_transaction_id: Optional[int] = None  # for refunds linked to original purchase

    @field_validator("amount")
    @classmethod
    def validate_finite_amount(cls, v: Decimal) -> Decimal:
        if not v.is_finite() or v.is_nan():
            raise ValueError("Amount must be a finite numerical value.")
        return v


class FinancialSummary(BaseModel):
    """
    Aggregate financials computed from categorized transactions.

    Clearly separates confirmed figures from unresolved items so that
    the operating result is marked provisional if unresolved items exist.
    """
    total_income: Decimal = Decimal("0.00")         # Confirmed positive client revenue
    total_expenses: Decimal = Decimal("0.00")       # Confirmed gross operating expenses
    total_refunds: Decimal = Decimal("0.00")        # All refunds received
    matched_refunds: Decimal = Decimal("0.00")      # Refunds safely linked to an expense category
    unmatched_refunds: Decimal = Decimal("0.00")    # Unmatched refunds held in review (not deducted)
    total_transfers: Decimal = Decimal("0.00")      # Internal transfers (excluded from P&L)
    total_fees: Decimal = Decimal("0.00")           # Bank & payment processing fees
    net_expenses: Decimal = Decimal("0.00")         # total_expenses - matched_refunds
    net_operating_result: Decimal = Decimal("0.00") # total_income - net_expenses - total_fees
    transaction_count: int = 0
    needs_review_count: int = 0
    unclassified_amount: Decimal = Decimal("0.00")  # Absolute dollar volume of unresolved items
    duplicate_count: int = 0                        # Number of flagged possible duplicates
    is_provisional: bool = False                    # True if unresolved items or unmatched refunds exist
    category_totals: dict[str, Decimal] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------

class TransactionUpdate(BaseModel):
    """Payload when correcting a single transaction's category/type."""
    transaction_type: TransactionType
    business_category: BusinessCategory


class TransactionCorrectionRequest(BaseModel):
    """Request to update a single transaction within a list and recalculate summary."""
    transaction_id: int
    update: TransactionUpdate
    transactions: list[CategorizedTransaction]


class RecalculateRequest(BaseModel):
    """Full set of transactions sent back for summary recalculation."""
    transactions: list[CategorizedTransaction]


class ParseResponse(BaseModel):
    """Response from the parse endpoint."""
    transactions: list[CategorizedTransaction]
    summary: FinancialSummary
    warnings: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
