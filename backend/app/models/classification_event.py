"""Classification event ORM model."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.transaction import Transaction


class ClassificationEventType:
    """Documented supported event types for audit tracking."""

    AUTO_CLASSIFIED = "AUTO_CLASSIFIED"
    MANUAL_CORRECTION = "MANUAL_CORRECTION"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    RULE_RECLASSIFICATION = "RULE_RECLASSIFICATION"

    ALL = {
        AUTO_CLASSIFIED,
        MANUAL_CORRECTION,
        MANUAL_OVERRIDE,
        RULE_RECLASSIFICATION,
    }


class ClassificationEvent(Base):
    """Classification events table tracking category decision history and audit trail."""

    __tablename__ = "classification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    previous_category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    new_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(32), default=ClassificationEventType.AUTO_CLASSIFIED, nullable=False, index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="classification_events"
    )
    previous_category: Mapped[Optional["Category"]] = relationship(
        "Category", foreign_keys=[previous_category_id]
    )
    new_category: Mapped["Category"] = relationship(
        "Category", foreign_keys=[new_category_id]
    )

    def __repr__(self) -> str:
        return (
            f"<ClassificationEvent(id={self.id}, tx_id={self.transaction_id}, "
            f"type={self.event_type!r}, new_cat={self.new_category_id})>"
        )
