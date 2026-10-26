from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class Direction(StrEnum):
    IN = "in"  # money into the account (payouts, refunds, transfers in)
    OUT = "out"  # money out of the account (purchases, fees, transfers out)
    ANY = "any"  # only used by rules

    @classmethod
    def of(cls, amount: Decimal) -> Direction:
        return cls.IN if amount > 0 else cls.OUT


class Source(StrEnum):
    """Where a decision came from, strongest first."""

    USER_RULE = "user_rule"
    KNOWLEDGE_BASE = "knowledge_base"
    KEYWORD = "keyword"
    FUZZY = "fuzzy"
    BANK_CATEGORY = "bank_category"
    NONE = "none"


class Flag(StrEnum):
    REFUND = "refund"
    LARGE_AMOUNT = "large_amount"
    SMALL_AMOUNT = "small_amount"
    DIRECTION_MISMATCH = "direction_mismatch"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    ALREADY_IMPORTED = "already_imported"
    AMBIGUOUS_MERCHANT = "ambiguous_merchant"
    UNKNOWN_DEPOSIT = "unknown_deposit"


@dataclass(frozen=True, slots=True)
class TransactionInput:
    description: str
    amount: Decimal  # signed: positive = money in, negative = money out
    bank_category: str | None = None


@dataclass(slots=True)
class Decision:
    merchant: str
    merchant_key: str
    category: str | None
    confidence: float
    needs_review: bool
    source: Source
    reasons: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)

    def send_to_review(self, reason: str, *, cap: float = 0.6, flag: Flag | None = None) -> None:
        """Withdraw the guess: the best guess becomes the first suggestion, not the answer."""
        self.needs_review = True
        self.confidence = min(self.confidence, cap)
        self.reasons.append(reason)
        if flag and flag not in self.flags:
            self.flags.append(flag)
        if self.category:
            if self.category in self.suggestions:
                self.suggestions.remove(self.category)
            self.suggestions.insert(0, self.category)
            self.category = None
