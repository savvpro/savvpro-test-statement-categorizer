
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class Statement(Base):
    __tablename__ = "statements"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    transaction_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    transactions = relationship(
        "Transaction",
        back_populates="statement",
        cascade="all, delete-orphan",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(
        Integer,
        ForeignKey("statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(String(10), nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=True)
    balance = Column(Float, nullable=True)
    category = Column(String(100), nullable=False, default="Needs Review")
    status = Column(String(30), nullable=False, default="needs_review")
    reason = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(String(30), nullable=False, default="none")
    exclude_from_spending = Column(Boolean, nullable=False, default=True)
    source_row = Column(Integer, nullable=True)
    corrected_category = Column(String(100), nullable=True)

    statement = relationship("Statement", back_populates="transactions")
