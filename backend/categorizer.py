
import re

CATEGORIES = [
    "Inventory and Supplies",
    "Shipping and Delivery",
    "Advertising and Marketing",
    "Platform Fees",
    "Software",
    "Utilities",
    "Refund",
    "Transfer - Not Spending",
    "Income",
    "Needs Review",
]

# Known descriptions and the categories they map to.
MERCHANT_RULES = {
    "PACKAGING SUPPLIES": "Inventory and Supplies",
    "WHOLESALE GOODS": "Inventory and Supplies",
    "SHIPPING LABEL": "Shipping and Delivery",
    "COURIER SERVICE": "Shipping and Delivery",
    "SOCIAL MEDIA ADS": "Advertising and Marketing",
    "AD CAMPAIGN": "Advertising and Marketing",
    "SHOP PLATFORM FEE": "Platform Fees",
    "PAYMENT PROCESSOR FEE": "Platform Fees",
    "CLOUDHOST": "Software",
    "DESIGN SOFTWARE": "Software",
    "INTERNET BILL": "Utilities",
}


def categorize_transaction(description: str, amount: float) -> dict:
    """Categorize a transaction using explicit rules."""

    if not description or not description.strip():
        return {
            "category": "Needs Review",
            "reason": "Transaction description is missing.",
        }

    normalized = re.sub(r"\s+", " ", description.upper()).strip()

    # Transfers are not business spending or income.
    if "TRANSFER" in normalized:
        return {
            "category": "Transfer - Not Spending",
            "reason": "Description indicates a transfer.",
        }

    # Refunds are money returned, not new income.
    if "REFUND" in normalized:
        return {
            "category": "Refund",
            "reason": "Description indicates a refund.",
        }

    # Match known merchant descriptions.
    for merchant, category in MERCHANT_RULES.items():
        if merchant in normalized:
            return {
                "category": category,
                "reason": f"Matched known merchant rule: {merchant}.",
            }

    # A positive amount alone is not enough to identify income.
    if amount > 0:
        return {
            "category": "Needs Review",
            "reason": (
                "Positive amount with no recognized description; "
                "could be income, a refund, or another transaction."
            ),
        }

    return {
        "category": "Needs Review",
        "reason": "No matching rule was found.",
    }
