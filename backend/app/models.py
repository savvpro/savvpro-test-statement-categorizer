"""Domain models shared by the parser, the brain, the service and the API."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from .categories import Category, Kind

# Money is a Decimal everywhere in the backend (floats drift: 0.1 + 0.2 != 0.3) and
# is written to JSON as a number so the UI can format it directly.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class Decision(BaseModel):
    """What the brain concluded about one transaction, and why."""

    model_config = ConfigDict(frozen=True)

    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str  # shown in the UI, so it is written for the driver, not for developers
    # When the brain sends a row to review it can still say which way it leans.
    suggestion: Category | None = None
    # For refunds: the expense category the refund most likely belongs to.
    related_category: Category | None = None


class Transaction(BaseModel):
    id: str = Field(default_factory=_new_id)
    row: int  # line number in the uploaded file, so the user can find it
    date: date
    description: str
    amount: Money  # negative = money out, positive = money in
    category: Category = Category.NEEDS_REVIEW
    confidence: float = 0.0
    reason: str = ""
    suggestion: Category | None = None
    related_category: Category | None = None
    user_fixed: bool = False

    def apply(self, decision: Decision) -> None:
        self.category = decision.category
        self.confidence = decision.confidence
        self.reason = decision.reason
        self.suggestion = decision.suggestion
        self.related_category = decision.related_category


class CategoryTotal(BaseModel):
    category: Category
    kind: Kind
    count: int
    total: Money  # signed: money out is negative


class TaxSummary(BaseModel):
    """The numbers a driver needs at tax time. Magnitudes are positive unless noted."""

    income: Money
    deductible_expenses: Money  # business expenses, already reduced by matching refunds
    refunds_netted: Money  # refunds that were subtracted from deductible_expenses
    personal_spending: Money  # not deductible
    other_refunds: Money  # refunds we could not tie to a business expense
    not_spending: Money  # transfers and card payments, net (signed)
    estimated_profit: Money  # income - deductible_expenses (signed)
    needs_review_count: int
    needs_review_in: Money  # unresolved money in
    needs_review_out: Money  # unresolved money out
    complete: bool  # False while rows still need review: the numbers above may change


class Summary(BaseModel):
    total_transactions: int
    needs_review: int
    by_category: list[CategoryTotal]
    tax: TaxSummary


class RowIssue(BaseModel):
    """A problem with one line of the uploaded file."""

    row: int
    message: str


class Statement(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)  # unguessable: there is no login
    filename: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    transactions: list[Transaction]
    skipped: list[RowIssue] = Field(default_factory=list)  # rows we could not read
    warnings: list[RowIssue] = Field(default_factory=list)  # rows we read but want checked
    # merchant (normalised description) -> category, filled in when the user fixes a row.
    # Scoped to this statement: with no accounts, a shared memory would leak between users.
    learned: dict[str, Category] = Field(default_factory=dict)
