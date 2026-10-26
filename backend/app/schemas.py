from datetime import date
from decimal import Decimal

from pydantic import BaseModel

NEEDS_REVIEW = "Needs Review"
REVIEW_THRESHOLD = 0.7


class Transaction(BaseModel):
    id: int
    date: date
    description: str
    normalized: str = ""
    amount: Decimal  # signed PKR: credit positive, debit negative
    balance: Decimal | None = None
    usd_hint: bool = False
    category: str = NEEDS_REVIEW
    confidence: float = 0.0
    reason: str = "Not categorized yet"
    needs_review: bool = True
    flags: list[str] = []
    user_edited: bool = False
    refund_of: int | None = None  # id of the purchase a Refund row pays back

    def assign(self, category: str, confidence: float, reason: str) -> None:
        """Set the result. Anything under the threshold is demoted to Needs Review."""
        if category != NEEDS_REVIEW and confidence < REVIEW_THRESHOLD:
            reason += (
                f" [confidence {confidence:.2f} below {REVIEW_THRESHOLD}; suggested {category}]"
            )
            category = NEEDS_REVIEW
        self.category = category
        self.confidence = confidence
        self.reason = reason
        self.needs_review = category == NEEDS_REVIEW


class UploadResponse(BaseModel):
    transactions: list[Transaction]
    skipped_rows: list[str]  # bad CSV rows that were left out, with line numbers


class CategoryUpdate(BaseModel):
    category: str


class CategoryTotal(BaseModel):
    category: str
    count: int
    net: Decimal  # signed PKR: credits positive, debits negative; matched refunds offset their purchase


class Summary(BaseModel):
    categories: list[CategoryTotal]
    total_income: Decimal
    total_spending: (
        Decimal  # positive PKR; excludes Transfer, Refund and Income, net of matched refunds
    )
    needs_review_count: int
