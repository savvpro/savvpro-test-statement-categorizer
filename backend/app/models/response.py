
from pydantic import BaseModel

from app.models.transaction import CategorizedTransaction


class CategoryTotal(BaseModel):
    category: str
    count: int
    total_amount: float
    percentage_of_expenses: float = 0.0


class StatementSummary(BaseModel):
    total_transactions: int
    total_income: float
    total_expenses: float
    total_transfers: float
    total_refunds: float
    needs_review_count: int
    duplicate_count: int
    review_progress_percent: float


class CategorizationResponse(BaseModel):
    filename: str
    transactions: list[CategorizedTransaction]
    category_totals: list[CategoryTotal]
    summary: StatementSummary


class UpdateCategoryRequest(BaseModel):
    transaction_id: str
    new_category: str
    save_as_rule: bool = False
    rule_pattern: str | None = None
