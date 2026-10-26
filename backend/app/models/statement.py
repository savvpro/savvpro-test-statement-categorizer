"""Statement ORM model."""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction


# Documented valid statement status states
class StatementStatus:
    """Allowed values for Statement.status."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"

    ALL = {PENDING, COMPLETED, COMPLETED_WITH_ERRORS, FAILED}


class Statement(Base):
    """Statements table tracking imported statement files."""

    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=StatementStatus.PENDING, nullable=False, index=True
    )
    transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True, default="USD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Deliberate non-cascading relationship: statements cannot silently delete financial records
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="statement",
        passive_deletes=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Statement(id={self.id}, filename={self.original_filename!r}, "
            f"status={self.status!r}, count={self.transaction_count})>"
        )
