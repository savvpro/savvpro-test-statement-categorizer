import re
from decimal import Decimal, InvalidOperation
from typing import Any


CATEGORY_NEEDS_REVIEW = "Needs Review"
CATEGORIES = (
    "Software",
    "Office Supplies",
    "Travel",
    "Meals",
    "Advertising",
    "Professional Services",
    "Banking Fees",
    "Refund",
    "Transfer",
    "Personal",
    CATEGORY_NEEDS_REVIEW,
)

MERCHANT_RULES = {
    "adobe": "Software",
    "figma": "Software",
    "github": "Software",
    "google ads": "Advertising",
}

KEYWORD_RULES = {
    "software": ("hosting", "domain renewal", "software license"),
    "office supplies": ("office depot", "staples", "printer ink", "stationery"),
    "travel": ("uber", "lyft", "hotel", "airline", "train", "parking"),
    "meals": ("client lunch", "business lunch", "business dinner"),
    "advertising": ("advertising", "ad campaign", "marketing"),
    "professional services": ("accounting", "accountant", "bookkeeping", "attorney"),
    "banking fees": ("monthly fee", "foreign transaction fee", "service charge"),
    "personal": ("personal grocery", "personal entertainment"),
}


def _normalized_description(description: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", description.lower()).strip()


def _result(category: str, confidence: str, reason: str) -> dict[str, str | bool]:
    return {
        "category": category,
        "confidence": confidence,
        "reason": reason,
        "needs_review": category == CATEGORY_NEEDS_REVIEW,
    }


def categorize_transaction(transaction: dict[str, Any]) -> dict[str, str | bool]:
    description = str(transaction.get("description", ""))
    normalized = _normalized_description(description)
    if not normalized:
        return _result(CATEGORY_NEEDS_REVIEW, "low", "The transaction has no description.")

    amount = transaction.get("amount")
    try:
        Decimal(str(amount))
    except (InvalidOperation, TypeError):
        return _result(CATEGORY_NEEDS_REVIEW, "low", "The transaction amount is invalid.")

    if any(term in normalized for term in ("refund", "refunded", "returned purchase", "credit")):
        return _result("Refund", "high", "The description identifies a refund or credit.")

    if any(term in normalized for term in ("transfer", "card payment", "autopay", "payment")):
        return _result("Transfer", "high", "The description identifies movement of money.")

    merchant_matches = {
        category for merchant, category in MERCHANT_RULES.items() if merchant in normalized
    }
    if len(merchant_matches) == 1:
        category = merchant_matches.pop()
        return _result(category, "high", "The merchant matches a known business rule.")
    if len(merchant_matches) > 1:
        return _result(CATEGORY_NEEDS_REVIEW, "low", "The description matches multiple merchant rules.")

    keyword_matches = {
        category
        for category, keywords in KEYWORD_RULES.items()
        if any(keyword in normalized for keyword in keywords)
    }
    if len(keyword_matches) == 1:
        category = keyword_matches.pop()
        return _result(category.title(), "medium", "The description matches a category keyword.")
    if len(keyword_matches) > 1:
        return _result(CATEGORY_NEEDS_REVIEW, "low", "The description matches multiple categories.")

    return _result(CATEGORY_NEEDS_REVIEW, "low", "No trusted rule matches this merchant.")


def categorize_transactions(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {**transaction, **categorize_transaction(transaction)}
        for transaction in transactions
    ]


def summarize_transactions(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    category_totals: dict[str, Decimal] = {}
    spending_total = Decimal("0")
    refund_total = Decimal("0")
    transfer_total = Decimal("0")
    review_total = Decimal("0")

    for transaction in transactions:
        amount = Decimal(str(transaction["amount"]))
        category = str(transaction["category"])
        category_totals[category] = category_totals.get(category, Decimal("0")) + amount

        if category == "Refund":
            refund_total += amount
        elif category == "Transfer":
            transfer_total += amount
        else:
            spending_total += amount
        if transaction.get("needs_review"):
            review_total += amount

    return {
        "spending_total": str(spending_total),
        "refund_total": str(refund_total),
        "transfer_total": str(transfer_total),
        "review_total": str(review_total),
        "category_totals": {key: str(value) for key, value in category_totals.items()},
        "transaction_count": len(transactions),
        "review_count": sum(1 for transaction in transactions if transaction.get("needs_review")),
    }