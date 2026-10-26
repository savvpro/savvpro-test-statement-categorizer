"""Signals: each looks at one row and returns zero or more scored `Candidate`s."""

from dataclasses import dataclass

from app.brain.models import AccountType


@dataclass(frozen=True, slots=True)
class RowContext:
    text: str  # uppercased raw description, whitespace collapsed
    key: str  # merchant_key
    direction: str | None  # "in" | "out" | None for zero amounts
    account_type: AccountType


SCORES = {
    "user_rule": 0.99,
    "structural": 0.95,
    "merchant": 0.92,
    "pattern": 0.85,
    "fuzzy_min": 0.70,
    "fuzzy_max": 0.80,
    "keyword": 0.60,
}
