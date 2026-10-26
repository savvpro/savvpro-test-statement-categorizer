"""Pydantic models shared across the backend.

Amount convention (normalized by the parser):
  amount > 0  -> money going OUT (a charge / spend)
  amount < 0  -> money coming IN (refund, payment, credit)
"""
import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    row_number: int
    txn_date: dt.date | None = None
    description: str = ""
    amount: Decimal | None = None
    currency: str = "USD"
    raw: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors and self.amount is not None


class CategorizedTransaction(BaseModel):
    transaction: Transaction
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    needs_review: bool
    matched_rule: str | None = None
