from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Category(StrEnum):
    SOFTWARE = "Software & Subscriptions"
    CLOUD = "Cloud & Hosting"
    EQUIPMENT = "Equipment & Supplies"
    TRAVEL = "Travel & Transport"
    MEALS = "Meals & Entertainment"
    SERVICES = "Professional Services"
    TELECOM = "Internet & Telecom"
    FEES = "Bank Fees"
    INCOME = "Client Income"
    REFUND = "Refund"
    TRANSFER = "Transfer"
    REVIEW = "Needs Review"


EXPENSE_CATEGORIES = (
    Category.SOFTWARE,
    Category.CLOUD,
    Category.EQUIPMENT,
    Category.TRAVEL,
    Category.MEALS,
    Category.SERVICES,
    Category.TELECOM,
    Category.FEES,
)


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Category


class Transaction(BaseModel):
    id: int
    statement_id: int
    row_number: int
    date: str
    description: str
    amount: str
    transaction_type: str
    category: Category
    automatic_category: Category
    manual_category: Category | None
    explanation: str
    automatic_explanation: str
    needs_review: bool
    manually_corrected: bool
    possible_duplicate: bool
    duplicate_confirmed: bool


class Statement(BaseModel):
    id: int
    filename: str
    created_at: str
    transaction_count: int
    duplicate_count: int


class Summary(BaseModel):
    currency: str = "PKR"
    expenses: str
    income: str
    refunds: str
    transfers: str
    transfers_in: str
    transfers_out: str
    unclassified_in: str
    unclassified_out: str
    net_movement: str
    review_count: int
    transaction_count: int
    expense_categories: dict[str, str]


class StatementDetail(BaseModel):
    statement: Statement
    transactions: list[Transaction]
    summary: Summary
