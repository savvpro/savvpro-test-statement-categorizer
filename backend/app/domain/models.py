"""Plain domain objects shared by the parsers, the brain and the API layer."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class Kind(StrEnum):
    EXPENSE = "expense"
    NON_SPENDING = "non_spending"
    INCOME = "income"
    REVIEW = "review"


class Status(StrEnum):
    CATEGORIZED = "categorized"
    NEEDS_REVIEW = "needs_review"
    EXCLUDED = "excluded"
    USER_CORRECTED = "user_corrected"


class Flag(StrEnum):
    REFUND = "refund"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    FOREIGN_CURRENCY = "foreign_currency"
    LARGE_AMOUNT = "large_amount"
    AMBIGUOUS_MERCHANT = "ambiguous_merchant"
    UNMATCHED_REFUND = "unmatched_refund"


class Convention(StrEnum):
    NEGATIVE_IS_SPENDING = "negative_is_spending"
    POSITIVE_IS_SPENDING = "positive_is_spending"


class SourceFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"
    OFX = "ofx"
    CAMT053 = "camt053"  # ISO 20022 bank-to-customer statement (XML)
    MT940 = "mt940"  # SWIFT customer statement message


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    kind: Kind
    deductible: str | None  # "full" | "partial" | "none" | None


@dataclass(frozen=True)
class RawRow:
    """One transaction line as read from a file, before any interpretation of direction."""

    line: int
    date: date
    description: str
    # The parser sets either `amount` or a `debit`/`credit` pair.
    amount: Decimal | None = None  # single signed column, sign convention still unknown
    debit: Decimal | None = None  # money out (positive number)
    credit: Decimal | None = None  # money in (positive number)
    currency: str | None = None
    external_id: str | None = None  # e.g. OFX FITID


@dataclass(frozen=True)
class RejectedRow:
    line: int
    raw: str
    reason: str


@dataclass
class ParsedStatement:
    source_format: SourceFormat
    rows: list[RawRow] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Set by formats where the sign convention is defined by the format itself (OFX).
    convention_hint: Convention | None = None
    currency_hint: str | None = None


@dataclass(frozen=True)
class Transaction:
    id: str
    line: int
    date: date
    description: str
    merchant: str
    amount: Decimal  # as in the file
    spend_amount: Decimal  # positive = money out, negative = money in
    currency: str
    category_id: str
    category_name: str
    kind: Kind
    status: Status
    confidence: float
    reasons: tuple[str, ...] = ()
    flags: tuple[Flag, ...] = ()
    refund_of: str | None = None
    suggestions: tuple[str, ...] = ()  # category ids worth offering when status is needs_review

    def with_(self, **changes: Any) -> Transaction:
        return replace(self, **changes)


@dataclass(frozen=True)
class Statement:
    id: str
    filename: str
    currency: str
    created_at: datetime
    source_format: SourceFormat
    convention: Convention
    transactions: tuple[Transaction, ...]
    rejected_rows: tuple[RejectedRow, ...]
    warnings: tuple[str, ...]
