from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class TransactionType(StrEnum):
    DEBIT = "DEBIT"    # Expense / Money Out
    CREDIT = "CREDIT"  # Income / Refund / Money In


class RawTransaction(BaseModel):
    id: str
    date: date
    description: str
    amount: float
    transaction_type: TransactionType
    line_number: int
    raw_reference: str | None = None
    currency: str = "USD"


class CategorizedTransaction(BaseModel):
    id: str
    line_number: int
    date: date
    raw_description: str
    normalized_description: str
    amount: float
    transaction_type: TransactionType
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    needs_review: bool = False
    is_refund: bool = False
    refund_parent_id: str | None = None
    is_transfer: bool = False
    is_duplicate: bool = False
    is_personal_ambiguous: bool = False
    user_overridden: bool = False
    currency: str = "USD"
