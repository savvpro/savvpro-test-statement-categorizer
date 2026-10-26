import datetime as dt
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class Category(str, Enum):
    RENTAL_INCOME = "Rental Income"
    SECURITY_DEPOSIT = "Security Deposit"
    TRANSFER = "Transfer"
    MORTGAGE_PAYMENT = "Mortgage Payment"
    MORTGAGE_INTEREST = "Mortgage Interest"
    MORTGAGE_PRINCIPAL = "Mortgage Principal"
    PROPERTY_TAX = "Property Tax"
    INSURANCE = "Insurance"
    REPAIRS = "Repairs & Maintenance"
    UTILITIES = "Utilities"
    HOA_FEES = "HOA Fees"
    BANK_FEES = "Bank Fees"
    NEEDS_REVIEW = "Needs Review"


class LoanDetails(BaseModel):
    """What the landlord tells us about their mortgage (frozen = hashable)."""

    model_config = ConfigDict(frozen=True)

    original_principal: Decimal = Field(gt=0)
    annual_rate_percent: Decimal = Field(ge=0, le=50)  # 6.0 means 6%
    term_months: int = Field(ge=1, le=600)
    first_payment_date: dt.date


class Split(BaseModel):
    """One part of a transaction that covers more than one category."""

    category: Category
    amount: Decimal  # same sign convention: negative = money out


class RawTransaction(BaseModel):
    row_number: int
    date: dt.date
    description: str
    amount: Decimal


class CategorizedTransaction(BaseModel):
    id: int
    date: dt.date
    description: str
    normalized: str
    amount: Decimal
    category: Category
    confidence: float = Field(ge=0, le=1)
    explanation: str
    is_duplicate: bool = False
    splits: list[Split] = Field(default_factory=list)

    @computed_field
    @property
    def needs_review(self) -> bool:
        return self.category == Category.NEEDS_REVIEW