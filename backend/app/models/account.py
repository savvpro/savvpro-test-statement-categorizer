from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.statement import Statement
    from app.models.transaction import Transaction


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # checking | credit_card
    institution: Mapped[str] = mapped_column(String, nullable=False, default="")
    mask: Mapped[str] = mapped_column(String, nullable=False, default="")  # last-4
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    statements: Mapped[list[Statement]] = relationship(back_populates="account")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")
