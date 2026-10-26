import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.brain.models import AccountType, CategoryKind, TxnStatus
from app.schemas.common import Money


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    statement_id: int
    row_index: int
    date: dt.date
    description_raw: str
    merchant_key: str
    amount: Money
    category_id: str
    suggested_category_id: str | None
    confidence: float
    status: TxnStatus
    reasons: list[str]
    rule_id: str | None
    flags: list[str]
    is_pending: bool
    linked_transaction_id: int | None
    updated_at: dt.datetime


class StatementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    account_type: AccountType
    uploaded_at: dt.datetime
    row_count: int
    parse_errors: list[dict[str, Any]]


class StatementDetailOut(StatementOut):
    warnings: list[str]
    detected_format: dict[str, Any]
    review_count: int


class UploadOut(StatementDetailOut):
    transactions: list[TransactionOut]


class TransactionUpdate(BaseModel):
    category_id: str = Field(min_length=1)
    remember: bool = False


class TransactionUpdateOut(BaseModel):
    transaction: TransactionOut
    updated_count: int  # other transactions re-categorized by the learned rule


class CategoryTotal(BaseModel):
    category_id: str
    label: str
    kind: CategoryKind
    schedule_c_line: str | None
    count: int
    total: Money  # signed: < 0 money out, refunds already netted in
    deductible: Money


class SummaryOut(BaseModel):
    statement_id: int
    income: Money
    expenses: Money  # positive number: money spent on business expenses after refunds
    net: Money
    estimated_deductible: Money
    categories: list[CategoryTotal]  # income + expense categories
    non_operating: list[CategoryTotal]  # transfers, card payments, personal, ...
    unlinked_refunds: Money
    unlinked_refund_count: int
    needs_review_count: int
    needs_review_amount: Money  # sum of absolute amounts still waiting for a decision
    pending_count: int
    pending_amount: Money  # excluded from every total above


class MerchantRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_key: str
    category_id: str
    source: str
    hits: int
    created_at: dt.datetime
