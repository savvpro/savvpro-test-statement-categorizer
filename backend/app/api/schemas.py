import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, model_validator


class TransactionOut(BaseModel):
    id: int
    row_number: int
    date: dt.date | None
    description: str
    amount: Decimal | None
    currency: str
    category: str
    confidence: float
    reason: str
    needs_review: bool
    matched_rule: str | None
    errors: list[str]
    is_duplicate: bool
    duplicate_of: int | None
    user_corrected: bool


class CurrencySummary(BaseModel):
    currency: str
    total_spend: Decimal
    spend_by_category: dict[str, Decimal]
    other_by_category: dict[str, Decimal]


class SummaryOut(BaseModel):
    upload_id: str
    filename: str
    total_rows: int
    needs_review_count: int
    duplicate_count: int
    invalid_count: int
    currencies: list[CurrencySummary]


class UploadOut(BaseModel):
    upload_id: str
    filename: str
    summary: SummaryOut
    transactions: list[TransactionOut]


class CorrectionIn(BaseModel):
    category: str | None = None
    keep_duplicate: bool | None = None

    @model_validator(mode="after")
    def _need_one_field(self):
        if self.category is None and self.keep_duplicate is None:
            raise ValueError("Send 'category' and/or 'keep_duplicate'")
        return self


class CorrectionOut(BaseModel):
    transaction: TransactionOut
    also_updated: int
    summary: SummaryOut
