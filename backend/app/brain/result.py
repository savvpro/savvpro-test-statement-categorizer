from dataclasses import dataclass

NEEDS_REVIEW = "Needs Review"
TRANSFER = "Transfer (not spending)"
REFUND = "Refund"
INCOME = "Income"
DUPLICATE_IGNORE = "Duplicate (ignore)"


@dataclass(frozen=True)
class Decision:
    category: str
    confidence: str  # "high" | "low"
    reason: str