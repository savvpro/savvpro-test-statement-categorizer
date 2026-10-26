from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category
    from app.models.correction import Correction
    from app.models.statement import Statement


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_id: Mapped[str] = mapped_column(ForeignKey("statements.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    posted_date: Mapped[date] = mapped_column(Date, nullable=False)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    merchant: Mapped[str] = mapped_column(String, nullable=False, default="")
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="auto")
    # auto | needs_review | confirmed
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reasons: Mapped[str] = mapped_column(Text, default="[]")        # JSON list of strings
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String, nullable=False, default="")
    linked_txn_id: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    deductible_pct_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    statement: Mapped[Statement] = relationship(back_populates="transactions")
    account: Mapped[Account] = relationship(back_populates="transactions")
    category: Mapped[Category | None] = relationship()
    corrections: Mapped[list[Correction]] = relationship(back_populates="transaction")
