from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # = slug
    name: Mapped[str] = mapped_column(String, nullable=False)
    group: Mapped[str] = mapped_column(String, nullable=False)  # income | expense | non_pl
    schedule_c_line: Mapped[str | None] = mapped_column(String, nullable=True)
    deductible_pct: Mapped[int] = mapped_column(Integer, default=100)
    color: Mapped[str] = mapped_column(String, default="#64748b")
    icon: Mapped[str] = mapped_column(String, default="circle")
    description: Mapped[str] = mapped_column(String, default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
