import re
from typing import Any


def categorize_by_rules(description: str, amount: float = 0.0) -> dict[str, Any] | None:
    """Categorize clear transactions using explainable rules."""
    text = re.sub(r"\s+", " ", description).strip().lower()

    if not text:
        return None

    # Refunds must not be treated as income.
    if re.search(r"\b(refund|refunded|reversal|returned payment)\b", text):
        return {
            "category": "Refund",
            "status": "categorized",
            "reason": "Recognized refund or reversal.",
            "exclude_from_spending": True,
        }

    # Internal transfers are not spending.
    if re.search(
        r"\b(transfer to savings|transfer from savings|"
        r"internal transfer|between accounts|own account transfer)\b",
        text,
    ):
        return {
            "category": "Transfer",
            "status": "categorized",
            "reason": "Recognized transfer between accounts.",
            "exclude_from_spending": True,
        }

    # Credit card bill payments are not new spending.
    if re.search(
        r"\b(credit card payment|card payment|payment to card|"
        r"credit card bill)\b",
        text,
    ):
        return {
            "category": "Transfer",
            "status": "categorized",
            "reason": "Recognized credit card payment; avoid double-counting.",
            "exclude_from_spending": True,
        }

    rules = [
        (r"\b(adobe|microsoft 365|office 365|google workspace|"
         r"software|github subscription)\b", "Software"),
        (r"\b(uber|lyft|taxi|cab|careem|in.?drive)\b", "Transportation"),
        (r"\b(grocery|groceries|supermarket|walmart|"
         r"carrefour|al.?fatah)\b", "Groceries"),
        (r"\b(restaurant|coffee shop|foodpanda|"
         r"ubereats|food delivery)\b", "Restaurants"),
        (r"\b(netflix|spotify|subscription|prime video)\b", "Subscription"),
        (r"\b(salary|payroll|wages)\b", "Income"),
        (r"\b(electricity|gas bill|water bill|utility bill|"
         r"k.?electric|lesco)\b", "Utilities"),
        (r"\b(hospital|pharmacy|medical|clinic|healthcare)\b", "Healthcare"),
        (r"\b(airline|flight|hotel|booking\.com|airbnb)\b", "Travel"),
    ]

    for pattern, category in rules:
        if re.search(pattern, text):
            return {
                "category": category,
                "status": "categorized",
                "reason": f"Matched a known transaction pattern for {category}.",
                "exclude_from_spending": category == "Income",
            }

    return {
        "category": "Needs Review",
        "status": "needs_review",
        "reason": "No reliable rule matched this transaction.",
        "exclude_from_spending": True,
    }