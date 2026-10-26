"""The fixed list of categories and how each one counts towards totals."""

NEEDS_REVIEW = "Needs Review"
REFUND = "Refund"
INCOME = "Income"
TRANSFER = "Transfer (not spending)"
CARD_PAYMENT = "Card Payment (not spending)"

SPENDING_CATEGORIES = (
    "Software & Subscriptions",
    "Travel",
    "Meals",
    "Office Supplies",
    "Internet & Phone",
    "Advertising",
    "Bank Fees",
    "Personal",
)
NOT_SPENDING_CATEGORIES = (TRANSFER, CARD_PAYMENT)

CATEGORIES: tuple[str, ...] = (
    "Software & Subscriptions",
    "Travel",
    "Meals",
    "Office Supplies",
    "Internet & Phone",
    "Advertising",
    "Bank Fees",
    INCOME,
    REFUND,
    TRANSFER,
    CARD_PAYMENT,
    "Personal",
    NEEDS_REVIEW,
)


def category_kind(category: str) -> str:
    """'spending' | 'refund' | 'income' | 'not_spending' | 'review'."""
    if category in SPENDING_CATEGORIES:
        return "spending"
    if category == REFUND:
        return "refund"
    if category == INCOME:
        return "income"
    if category in NOT_SPENDING_CATEGORIES:
        return "not_spending"
    return "review"
