"""Pure domain types shared by parsing, the brain and services. No DB imports here."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


class AccountType(StrEnum):
    checking = "checking"
    credit_card = "credit_card"


class CategoryKind(StrEnum):
    expense = "expense"
    income = "income"
    non_operating = "non_operating"
    review = "review"


class TxnStatus(StrEnum):
    auto = "auto"
    needs_review = "needs_review"
    user_confirmed = "user_confirmed"


class SignalSource(StrEnum):
    user_rule = "user_rule"
    structural = "structural"
    merchant = "merchant"
    pattern = "pattern"
    fuzzy = "fuzzy"
    keyword = "keyword"
    context = "context"


@dataclass(frozen=True, slots=True)
class ParsedRow:
    """One statement line after parsing. `amount > 0` is money in, `amount < 0` is money out."""

    row_index: int
    date: date
    description: str
    amount: Decimal
    is_pending: bool = False
    raw: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError(f"amount must be Decimal, got {type(self.amount).__name__}")


@dataclass(frozen=True, slots=True)
class Candidate:
    """A single signal's vote for a category."""

    category_id: str
    score: float
    reason: str
    source: SignalSource
    rule_id: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be within 0..1, got {self.score}")


@dataclass(slots=True)
class Decision:
    """The brain's final verdict for one row."""

    category_id: str
    confidence: float
    status: TxnStatus
    merchant_key: str
    reasons: list[str] = field(default_factory=list)
    suggested_category_id: str | None = None
    rule_id: str | None = None
    flags: list[str] = field(default_factory=list)
    linked_row_index: int | None = None  # refund -> original purchase row
