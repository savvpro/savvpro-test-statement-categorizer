"""ORM tables (01-architecture section 5)."""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Statement(Base):
    __tablename__ = "statements"
    __table_args__ = (UniqueConstraint("file_sha256", name="uq_statements_file_sha256"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    source_format: Mapped[str] = mapped_column(String(8))
    account_type: Mapped[str] = mapped_column(String(16))
    file_sha256: Mapped[str] = mapped_column(String(64))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class TransactionRow(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("statement_id", "row_index", name="uq_txn_statement_row"),
        Index("ix_txn_statement_merchant", "statement_id", "merchant_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    statement_id: Mapped[str] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE"), index=True
    )
    row_index: Mapped[int] = mapped_column(Integer)
    posted_date: Mapped[date] = mapped_column(Date, index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    direction: Mapped[str] = mapped_column(String(8))
    description: Mapped[str] = mapped_column(Text)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    merchant_key: Mapped[str] = mapped_column(String(128), index=True)
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fitid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    is_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    brain_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_refund: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class MerchantRule(Base):
    __tablename__ = "merchant_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    merchant_key: Mapped[str] = mapped_column(String(128), unique=True)
    category: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    source_transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    from_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_category: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str] = mapped_column(String(16))
    remember: Mapped[bool] = mapped_column(Boolean, default=False)
    applied_to_similar: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
