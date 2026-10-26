from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    before: Mapped[str] = mapped_column(Text, nullable=False)  # JSON snapshot
    after: Mapped[str] = mapped_column(Text, nullable=False)   # JSON snapshot
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transaction: Mapped[Transaction] = relationship(back_populates="corrections")
