"""Pure domain data structures. No framework imports allowed here."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from app.domain.enums import AccountType, Category, Direction, Flag, Status


@dataclass(frozen=True, slots=True)
class ParseWarning:
    code: str
    message: str
    row_index: int | None = None


@dataclass(frozen=True, slots=True)
class RawTransaction:
    """One row exactly as read from the file, before any interpretation."""

    row_index: int
    date_raw: str
    description_raw: str
    amount_raw: str | None = None
    debit_raw: str | None = None
    credit_raw: str | None = None
    memo_raw: str | None = None
    type_raw: str | None = None
    status_raw: str | None = None
    fitid: str | None = None
    extra: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ParseResult:
    rows: tuple[RawTransaction, ...]
    warnings: tuple[ParseWarning, ...]
    date_format: str | None = None  # chosen strptime format (CSV) or "ofx"
    decimal_comma: bool = False
    account_type_hint: AccountType | None = None  # e.g. from OFX ACCTTYPE


@dataclass(frozen=True, slots=True)
class Transaction:
    """A normalized transaction. amount_cents is signed: + inflow, - outflow."""

    row_index: int
    posted_date: date
    amount_cents: int
    direction: Direction
    description: str
    memo: str | None
    merchant_key: str
    channel: str | None
    counterparty: str | None
    account_type: AccountType
    fitid: str | None
    fingerprint: str
    is_pending: bool = False


@dataclass(frozen=True, slots=True)
class Candidate:
    category: Category
    score: float
    source: str
    rule_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class Decision:
    category: Category | None
    status: Status
    confidence: float
    reasons: tuple[str, ...]
    rule_ids: tuple[str, ...]
    flags: frozenset[Flag]
    is_refund: bool = False
    duplicate_of_row: int | None = None
    suggestion: Category | None = None
