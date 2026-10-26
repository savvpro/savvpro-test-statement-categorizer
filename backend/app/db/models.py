import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.brain.models import AccountType, TxnStatus
from app.db.base import Base
from app.db.money import from_cents, to_cents


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    account_type: Mapped[AccountType] = mapped_column(SAEnum(AccountType, native_enum=False))
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    parse_errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    detected_format: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # sha256 of the uploaded bytes; NULL for statements created outside an upload.
    file_hash: Mapped[str | None] = mapped_column(String(64), unique=True)

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="statement",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Transaction.row_index",
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("statement_id", "row_index"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE"), index=True
    )
    row_index: Mapped[int] = mapped_column(Integer)
    date: Mapped[dt.date] = mapped_column(Date)
    description_raw: Mapped[str] = mapped_column(Text)
    merchant_key: Mapped[str] = mapped_column(String(255), index=True, default="")
    # Money is stored as integer cents; use the `amount` property for Decimal access.
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    category_id: Mapped[str] = mapped_column(String(64))
    suggested_category_id: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[TxnStatus] = mapped_column(SAEnum(TxnStatus, native_enum=False))
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_id: Mapped[str | None] = mapped_column(String(128))
    flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL")
    )
    dedupe_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    statement: Mapped[Statement] = relationship(back_populates="transactions")
    linked_transaction: Mapped["Transaction | None"] = relationship(remote_side=[id])

    @property
    def amount(self) -> Decimal:
        return from_cents(self.amount_cents)

    @amount.setter
    def amount(self, value: Decimal) -> None:
        self.amount_cents = to_cents(value)


class MerchantRule(Base):
    __tablename__ = "merchant_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_key: Mapped[str] = mapped_column(String(255), unique=True)
    category_id: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32), default="user")
    hits: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
