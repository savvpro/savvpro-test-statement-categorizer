from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    profile_name: Mapped[str] = mapped_column(String(64))
    account_type: Mapped[str] = mapped_column(String(16))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime)  # UTC
    skipped_count: Mapped[int] = mapped_column(default=0)  # blank lines, kept only as a count


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE"), index=True
    )
    row_number: Mapped[int]
    date: Mapped[date] = mapped_column(Date)
    raw_description: Mapped[str] = mapped_column(Text)
    merchant_key: Mapped[str] = mapped_column(String(255), index=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger)  # negative = money out
    currency: Mapped[str] = mapped_column(String(8))
    category: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    rule_id: Mapped[str | None] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(Boolean)
    suggested_category: Mapped[str | None] = mapped_column(String(64))
    edited_by_user: Mapped[bool] = mapped_column(Boolean, default=False)


class ParseErrorRow(Base):
    __tablename__ = "parse_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE"), index=True
    )
    row_number: Mapped[int]
    raw_line: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)


class UserRuleRow(Base):
    __tablename__ = "user_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_key: Mapped[str] = mapped_column(String(255), unique=True)
    category: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime)  # UTC
