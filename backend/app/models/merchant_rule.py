"""Merchant rule ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category


class RuleMatchType:
    """Documented supported match types for MerchantRule."""

    EXACT = "EXACT"
    CONTAINS = "CONTAINS"
    REGEX = "REGEX"

    ALL = {EXACT, CONTAINS, REGEX}


class MerchantRule(Base):
    """Merchant rules table preparing schema for user-defined reusable rules."""

    __tablename__ = "merchant_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    match_type: Mapped[str] = mapped_column(
        String(32), default=RuleMatchType.CONTAINS, nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="rules")

    def __repr__(self) -> str:
        return (
            f"<MerchantRule(id={self.id}, pattern={self.merchant_pattern!r}, "
            f"type={self.match_type!r}, category_id={self.category_id}, priority={self.priority})>"
        )
