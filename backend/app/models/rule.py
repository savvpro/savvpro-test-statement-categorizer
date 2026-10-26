from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    match_type: Mapped[str] = mapped_column(String, nullable=False)
    # merchant_exact | contains | regex
    pattern: Mapped[str] = mapped_column(String, nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    amount_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String, default="user")  # user | correction
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
