"""SQLModel ORM models – the single source of truth for the DB schema."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Column, Field, SQLModel, String


# ── Enums ────────────────────────────────────────────────────────────────────

class AccountType(str, Enum):
    CREDIT_CARD = "credit_card"
    CHECKING = "checking"


class TxnStatus(str, Enum):
    AUTO = "auto"
    SUGGESTED = "suggested"
    NEEDS_REVIEW = "needs_review"
    USER_CONFIRMED = "user_confirmed"


class MatchType(str, Enum):
    EXACT = "exact"
    CONTAINS = "contains"
    REGEX = "regex"


# ── Statement ────────────────────────────────────────────────────────────────

class Statement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    account_type: AccountType = Field(sa_column=Column(String))
    account_label: str = ""
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    file_hash: str = Field(index=True)
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    row_count: int = 0


# ── Transaction ──────────────────────────────────────────────────────────────

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    statement_id: int = Field(foreign_key="statement.id", index=True)
    row_index: int

    posted_date: date
    raw_description: str
    merchant_key: str = ""

    amount_cents: int          # negative = debit, positive = credit
    currency: str = "USD"

    category: str = "needs_review"
    confidence: float = 0.0
    status: TxnStatus = Field(
        default=TxnStatus.NEEDS_REVIEW,
        sa_column=Column(String),
    )
    reason: str = ""
    rule_id: Optional[int] = Field(default=None, foreign_key="userrule.id")

    # JSON-encoded list of flag strings
    flags_json: str = "[]"

    linked_txn_id: Optional[int] = Field(default=None, foreign_key="transaction.id")
    deductible_pct: int = 100

    fingerprint: str = Field(default="", index=True)
    user_note: str = ""

    # ── helpers ──────────────────────────────────────────────────────────
    @property
    def flags(self) -> list[str]:
        return json.loads(self.flags_json) if self.flags_json else []

    @flags.setter
    def flags(self, value: list[str]) -> None:
        self.flags_json = json.dumps(value)

    @property
    def amount_dollars(self) -> str:
        """Human-readable dollar string (never float arithmetic)."""
        sign = "-" if self.amount_cents < 0 else ""
        abs_cents = abs(self.amount_cents)
        return f"{sign}${abs_cents // 100}.{abs_cents % 100:02d}"


# ── User Rule ────────────────────────────────────────────────────────────────

class UserRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    match_type: MatchType = Field(sa_column=Column(String))
    pattern: str
    category: str
    min_cents: Optional[int] = None
    max_cents: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = 0


# ── User ─────────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str = ""
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

