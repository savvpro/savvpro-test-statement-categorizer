"""Transaction ORM model."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.classification_event import ClassificationEvent
    from app.models.statement import Statement


class ReviewStatus:
    """Documented valid states for Transaction.review_status."""

    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    NOT_REQUIRED = "NOT_REQUIRED"

    ALL = {PENDING, REVIEWED, NOT_REQUIRED}


class Transaction(Base):
    """Transactions table representing categorized financial entries."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("statements.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    original_description: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Monetary precision: DECIMAL(15,2) enforces exact decimal safety up to trillions
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    classification_reason: Mapped[str] = mapped_column(String(500), nullable=False)

    review_status: Mapped[str] = mapped_column(
        String(32), default=ReviewStatus.PENDING, nullable=False, index=True
    )
    was_manually_categorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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
    statement: Mapped["Statement"] = relationship("Statement", back_populates="transactions")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="transactions")
    classification_events: Mapped[List["ClassificationEvent"]] = relationship(
        "ClassificationEvent", back_populates="transaction"
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, date={self.transaction_date}, "
            f"amount={self.amount}, category_id={self.category_id}, "
            f"review_status={self.review_status!r})>"
        )
