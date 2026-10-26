"""
Pydantic Models and Schemas for Statement Categorizer API.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class TransactionItem(BaseModel):
    id: str
    date: str
    raw_description: str
    amount: float
    transaction_type: str = "DEBIT"
    cleaned_merchant: str = ""
    category: str
    confidence: float
    reason: str
    needs_review: bool
    suggested_category: Optional[str] = None
    schedule_c_line: str
    deductibility_pct: float
    deductible_amount: float
    is_expense: Optional[bool] = None
    is_income: Optional[bool] = None
    tax_note: str = ""
    color: str = "#6366f1"
    user_overridden: bool = False
    notes: Optional[str] = None


class CategoryBreakdownItem(BaseModel):
    category: str
    schedule_c_line: str
    total_amount: float
    deductible_amount: float
    transaction_count: int
    deductibility_pct: float
    color: str
    tax_note: str


class TaxSummary(BaseModel):
    gross_income: float
    total_raw_expenses: float
    total_deductible_expenses: float
    total_refunds_offset: float
    total_non_expense_transfers: float
    net_taxable_profit: float
    total_transactions: int
    needs_review_count: int
    review_required_amount: float
    categories: List[CategoryBreakdownItem]


class CategorizationResponse(BaseModel):
    transactions: List[TransactionItem]
    tax_summary: TaxSummary
    applied_rules_count: int


class UpdateTransactionRequest(BaseModel):
    id: str
    new_category: str
    apply_to_merchant: bool = False
    notes: Optional[str] = None


class AddCustomRuleRequest(BaseModel):
    merchant_pattern: str
    category: str


class SampleDatasetMeta(BaseModel):
    id: str
    title: str
    subtitle: str
    description: str
    transaction_count: int
    tags: List[str]
