from decimal import Decimal

from pydantic import BaseModel

CANONICAL_CATEGORIES = [
    "Software",
    "Travel & Transport",
    "Meals & Coffee",
    "Office Supplies & Equipment",
    "Internet & Utilities",
    "Advertising & Marketing",
    "Professional Services",
    "Bank Fees",
    "Income",
    "Refund",
    "Transfer (not spending)",
    "Personal / Owner Draw",
    "Needs Review",
]

EXPENSE_CATEGORIES = [
    "Software",
    "Travel & Transport",
    "Meals & Coffee",
    "Office Supplies & Equipment",
    "Internet & Utilities",
    "Advertising & Marketing",
    "Professional Services",
    "Bank Fees",
]


class Transaction(BaseModel):
    id: str
    date: str
    original_date: str
    description: str
    normalized_description: str
    amount: Decimal
    direction: str  # 'expense', 'income', 'transfer', 'refund'
    category: str
    confidence: float
    reason: str
    needs_review: bool = False
    user_edited: bool = False
    notes: str | None = None
    is_duplicate: bool = False
    duplicate_reason: str | None = None


class ParseIssue(BaseModel):
    row_number: int
    raw_content: str
    issue: str


class CategorySummaryItem(BaseModel):
    category: str
    count: int
    total_amount: Decimal
    percentage: float
    deductible_note: str | None = None


class SummaryResponse(BaseModel):
    total_transactions: int
    total_expenses: Decimal
    total_income: Decimal
    total_refunds: Decimal
    total_transfers: Decimal
    total_needs_review_count: int
    total_needs_review_amount: Decimal
    net_operating_total: Decimal
    category_breakdown: list[CategorySummaryItem]


class StatementPreviewResponse(BaseModel):
    filename: str
    total_rows: int
    valid_rows: int
    rejected_rows: int
    issues: list[ParseIssue]
    transactions: list[Transaction]
    summary: SummaryResponse


class UpdateTransactionRequest(BaseModel):
    category: str
    notes: str | None = None


class BatchRecalculateRequest(BaseModel):
    transactions: list[Transaction]


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
