"""The category set for the supported use case: a freelance designer's business card.

Every category carries a kind so the rest of the system never has to special-case ids:
expense rows count as spending, non_spending rows (transfers, card payments) never do.
"""

from __future__ import annotations

from app.domain.models import Category, Kind

NEEDS_REVIEW = "needs_review"
TRANSFER = "transfer"
CARD_PAYMENT = "card_payment"
INCOME = "income"
BANK_FEES = "bank_fees"

_CATEGORIES: tuple[Category, ...] = (
    Category("software", "Software & Subscriptions", Kind.EXPENSE, "full"),
    Category("hosting", "Hosting & Domains", Kind.EXPENSE, "full"),
    Category("travel", "Travel & Transport", Kind.EXPENSE, "full"),
    Category("meals", "Meals & Entertainment", Kind.EXPENSE, "partial"),
    Category("office", "Office Supplies & Equipment", Kind.EXPENSE, "full"),
    Category("marketing", "Advertising & Marketing", Kind.EXPENSE, "full"),
    Category("professional", "Professional Services", Kind.EXPENSE, "full"),
    Category("telecom", "Phone & Internet", Kind.EXPENSE, "partial"),
    Category("education", "Education & Training", Kind.EXPENSE, "full"),
    Category("rent", "Rent & Coworking", Kind.EXPENSE, "full"),
    Category("insurance", "Insurance", Kind.EXPENSE, "full"),
    Category("taxes", "Taxes & Licences", Kind.EXPENSE, "full"),
    Category(BANK_FEES, "Bank Fees & Interest", Kind.EXPENSE, "full"),
    Category("personal", "Personal (Not Deductible)", Kind.EXPENSE, "none"),
    Category(TRANSFER, "Transfer (Not Spending)", Kind.NON_SPENDING, None),
    Category(CARD_PAYMENT, "Card Payment (Not Spending)", Kind.NON_SPENDING, None),
    Category(INCOME, "Client Income", Kind.INCOME, None),
    Category(NEEDS_REVIEW, "Needs Review", Kind.REVIEW, None),
)

CATEGORIES: dict[str, Category] = {c.id: c for c in _CATEGORIES}


def all_categories() -> list[Category]:
    return list(_CATEGORIES)


def get_category(category_id: str) -> Category | None:
    return CATEGORIES.get(category_id)


def require_category(category_id: str) -> Category:
    category = CATEGORIES.get(category_id)
    if category is None:
        raise KeyError(category_id)
    return category
