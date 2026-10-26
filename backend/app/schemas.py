import datetime as dt

from pydantic import BaseModel


class Transaction(BaseModel):
    id: str
    row: int
    date: dt.date
    raw_description: str
    description: str
    amount: float  # negative = money out, positive = money in
    currency: str = "USD"
    category: str = ""
    confidence: str = ""  # "high" | "low"
    reason: str = ""
    tax_deductible: str = "unknown"  # yes | partial | no | n/a | unknown
    user_overridden: bool = False


class SkippedRow(BaseModel):
    row: int
    reason: str


class CategoryTotal(BaseModel):
    category: str
    count: int
    total: float
    counted: bool  # False = totals mai shamil nahi (transfer, duplicate)


class Summary(BaseModel):
    by_category: list[CategoryTotal]
    income: float
    expenses: float
    refunds: float
    net_expenses: float
    needs_review_count: int


class UploadResponse(BaseModel):
    transactions: list[Transaction]
    skipped: list[SkippedRow]
    summary: Summary


class UpdateCategoryRequest(BaseModel):
    category: str


class UpdateResponse(BaseModel):
    transaction: Transaction
    summary: Summary