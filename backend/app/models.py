"""Pydantic schemas shared by the parser, the brain and the API."""

from pydantic import BaseModel, Field


class ParsedTransaction(BaseModel):
    """One row extracted from the statement, before categorization."""

    date_raw: str
    date: str | None = None  # ISO yyyy-mm-dd when parseable, else None
    description: str
    amount: float
    issues: list[str] = Field(default_factory=list)


class TransactionOut(BaseModel):
    """One categorized transaction returned to the frontend."""

    id: int
    date: str | None
    description: str
    normalized: str
    amount: float
    direction: str  # "in" | "out"
    category: str | None  # None => Needs Review (no confident category)
    linked_category: str | None = None  # refunds: which spend category it offsets
    confidence: float = 0.0
    band: str = "low"  # "high" | "medium" | "low"
    needs_review: bool = True
    is_spending: bool = False
    flags: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class Summary(BaseModel):
    """Statement-level totals. Spending is gross; refunds are reported separately."""

    by_category: dict[str, float] = Field(default_factory=dict)
    spending_total: float = 0.0
    income_total: float = 0.0
    refunds_total: float = 0.0
    transfers_total: float = 0.0
    review_count: int = 0
    count: int = 0


class ParseMeta(BaseModel):
    rows_read: int = 0
    rows_kept: int = 0
    rows_skipped: int = 0
    skipped_labels: list[str] = Field(default_factory=list)


class CategorizeResponse(BaseModel):
    filename: str
    transactions: list[TransactionOut]
    summary: Summary
    meta: ParseMeta
    warnings: list[str] = Field(default_factory=list)
