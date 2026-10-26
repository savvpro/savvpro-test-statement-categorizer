"""The category vocabulary.

Kept in one place so the rules file, the API and the UI cannot drift apart.
"""

from decimal import Decimal
from enum import StrEnum


class Category(StrEnum):
    INCOME = "Income"
    FUEL = "Fuel"
    CAR_MAINTENANCE = "Car Maintenance"
    TOLLS_PARKING = "Tolls & Parking"
    PHONE_INTERNET = "Phone & Internet"
    PLATFORM_FEES = "Platform Fees"
    PERSONAL = "Personal"
    TRANSFER = "Transfer"
    CARD_PAYMENT = "Card Payment"
    REFUND = "Refund"
    NEEDS_REVIEW = "Needs Review"


class Kind(StrEnum):
    """How a category behaves at tax time."""

    INCOME = "income"  # taxable money in
    DEDUCTIBLE = "deductible"  # business expense
    PERSONAL = "personal"  # spending that is not deductible
    EXCLUDED = "excluded"  # not spending at all (moving money around)
    REFUND = "refund"  # money back; reduces an expense, is not income
    REVIEW = "review"  # the brain was not sure


KIND: dict[Category, Kind] = {
    Category.INCOME: Kind.INCOME,
    Category.FUEL: Kind.DEDUCTIBLE,
    Category.CAR_MAINTENANCE: Kind.DEDUCTIBLE,
    Category.TOLLS_PARKING: Kind.DEDUCTIBLE,
    Category.PHONE_INTERNET: Kind.DEDUCTIBLE,
    Category.PLATFORM_FEES: Kind.DEDUCTIBLE,
    Category.PERSONAL: Kind.PERSONAL,
    Category.TRANSFER: Kind.EXCLUDED,
    Category.CARD_PAYMENT: Kind.EXCLUDED,
    Category.REFUND: Kind.REFUND,
    Category.NEEDS_REVIEW: Kind.REVIEW,
}

DEDUCTIBLE: frozenset[Category] = frozenset(c for c, k in KIND.items() if k is Kind.DEDUCTIBLE)

# Categories that only make sense for one direction of money.
INFLOW_ONLY: frozenset[Category] = frozenset({Category.INCOME, Category.REFUND})
OUTFLOW_ONLY: frozenset[Category] = DEDUCTIBLE | {Category.PERSONAL}

# What the user may pick when fixing a row.
ASSIGNABLE: tuple[Category, ...] = tuple(c for c in Category if c is not Category.NEEDS_REVIEW)


def sign_allows(category: Category, amount: Decimal) -> bool:
    """False when a category contradicts the direction of the money.

    A "Fuel" row cannot be money in, and "Income" cannot be money out. Transfers,
    card payments and Needs Review can go either way.
    """
    if category in INFLOW_ONLY:
        return amount > 0
    if category in OUTFLOW_ONLY:
        return amount < 0
    return True
