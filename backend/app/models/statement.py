from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.transaction import Transaction


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_sha256: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False, default="csv")
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_rows: Mapped[str] = mapped_column(Text, default="[]")   # JSON
    warnings: Mapped[str] = mapped_column(Text, default="[]")        # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped[Account] = relationship(back_populates="statements")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="statement")
