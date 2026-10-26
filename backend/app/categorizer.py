
import re


CATEGORY_RULES = {
    "Software & Subscriptions": [
        "adobe", "github", "notion", "figma", "canva",
        "microsoft 365", "google workspace",
    ],
    "Office Supplies": [
        "staples", "office depot", "stationery",
    ],
    "Travel": [
        "uber", "lyft", "airline", "flight", "hotel",
        "train ticket",
    ],
    "Meals": [
        "restaurant", "cafe", "coffee shop", "starbucks",
    ],
    "Utilities": [
        "electricity", "internet bill", "water bill",
    ],
}


TRANSFER_KEYWORDS = [
    "transfer", "payment to self", "own account",
    "internal transfer",
]

REFUND_KEYWORDS = [
    "refund", "reversal", "returned payment",
]


def categorize_transaction(description: str, amount: float) -> dict:
    """
    Categorize a transaction using explicit rules.

    Positive amount: money received.
    Negative amount: money spent.
    Amount convention must match the uploaded statement.
    """
    original_description = description or ""
    normalized = re.sub(r"\s+", " ", original_description.lower()).strip()

    # Transfers are movements of money, not spending or income.
    if any(keyword in normalized for keyword in TRANSFER_KEYWORDS):
        return {
            "category": "Transfer",
            "status": "Categorized",
            "reason": "Transaction matches a transfer rule.",
        }

    # Refunds should not be classified as ordinary income.
    if any(keyword in normalized for keyword in REFUND_KEYWORDS):
        return {
            "category": "Refund",
            "status": "Categorized",
            "reason": "Transaction matches a refund or reversal rule.",
        }

    # Known merchants are classified using our own rules.
    for category, keywords in CATEGORY_RULES.items():
        if any(keyword in normalized for keyword in keywords):
            return {
                "category": category,
                "status": "Categorized",
                "reason": f"Matched a known merchant or keyword for {category}.",
            }

    # Do not guess when a transaction is not recognized.
    return {
        "category": "Needs Review",
        "status": "Needs Review",
        "reason": "No sufficiently specific categorization rule matched.",
    }
