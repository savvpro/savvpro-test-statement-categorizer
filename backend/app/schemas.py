"""Pydantic v2 schemas – API boundary contracts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import AccountType, MatchType, TxnStatus


# ── Statement ────────────────────────────────────────────────────────────────

class StatementOut(BaseModel):
    id: int
    filename: str
    account_type: AccountType
    account_label: str
    period_start: Optional[date]
    period_end: Optional[date]
    uploaded_at: datetime
    row_count: int

    model_config = {"from_attributes": True}


class UploadResult(BaseModel):
    statement: StatementOut
    counts: StatusCounts


class StatusCounts(BaseModel):
    total: int = 0
    auto: int = 0
    suggested: int = 0
    needs_review: int = 0
    excluded: int = 0


# Forward-ref fix (UploadResult references StatusCounts)
UploadResult.model_rebuild()


# ── Transaction ──────────────────────────────────────────────────────────────

class TransactionOut(BaseModel):
    id: int
    statement_id: int
    row_index: int
    posted_date: date
    raw_description: str
    merchant_key: str
    amount_cents: int
    currency: str
    category: str
    confidence: float
    status: TxnStatus
    reason: str
    rule_id: Optional[int]
    flags: list[str]
    linked_txn_id: Optional[int]
    deductible_pct: int
    user_note: str

    model_config = {"from_attributes": True}


class TransactionPatch(BaseModel):
    category: Optional[str] = None
    user_note: Optional[str] = None
    save_rule: bool = False


class BulkPatch(BaseModel):
    ids: list[int]
    category: str
    save_rule: bool = False


class PaginatedTransactions(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


# ── Rules ────────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    match_type: MatchType = MatchType.EXACT
    pattern: str
    category: str
    min_cents: Optional[int] = None
    max_cents: Optional[int] = None


class RuleOut(BaseModel):
    id: int
    match_type: MatchType
    pattern: str
    category: str
    min_cents: Optional[int]
    max_cents: Optional[int]
    created_at: datetime
    hit_count: int

    model_config = {"from_attributes": True}


class RuleTestResult(BaseModel):
    pattern: str
    would_match: list[str]   # list of merchant_keys that would match


# ── Summary ──────────────────────────────────────────────────────────────────

class CategoryTotal(BaseModel):
    category: str
    label: str
    schedule_c_line: str
    cat_type: str
    total_cents: int
    deductible_cents: int
    deductible_pct: int
    count: int


class SummaryOut(BaseModel):
    statement_id: int
    totals: list[CategoryTotal]
    total_income_cents: int
    total_expense_cents: int
    total_deductible_cents: int
    total_excluded_cents: int
    net_cents: int
    status_counts: StatusCounts
    reconciles: bool
    reconciliation_note: str


# ── Errors ───────────────────────────────────────────────────────────────────

class ColumnMapping(BaseModel):
    """Sent back on 422 when headers can't be auto-detected."""
    available_columns: list[str]
    required_fields: list[str] = ["date", "description", "amount"]
    message: str = "Could not auto-detect columns. Please provide a mapping."


class ColumnMappingRequest(BaseModel):
    """User-supplied column mapping for ambiguous CSVs."""
    date_col: str
    description_col: str
    amount_col: Optional[str] = None       # single amount column
    debit_col: Optional[str] = None        # or separate debit/credit
    credit_col: Optional[str] = None
