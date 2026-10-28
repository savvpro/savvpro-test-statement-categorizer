"""The category list for a rideshare / delivery driver preparing Schedule C."""

from enum import Enum


class Kind(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    REFUND = "refund"
    NOT_SPENDING = "not_spending"
    REVIEW = "review"


# name -> (kind, deductible business expense?)
CATEGORIES: dict[str, tuple[Kind, bool]] = {
    "Platform Income": (Kind.INCOME, False),
    "Tips & Bonuses": (Kind.INCOME, False),
    "Fuel": (Kind.EXPENSE, True),
    "EV Charging": (Kind.EXPENSE, True),
    "Vehicle Maintenance": (Kind.EXPENSE, True),
    "Car Wash": (Kind.EXPENSE, True),
    "Tolls & Parking": (Kind.EXPENSE, True),
    "Phone & Data": (Kind.EXPENSE, True),
    "Vehicle Insurance": (Kind.EXPENSE, True),
    "Driver Supplies": (Kind.EXPENSE, True),
    "Business Apps & Fees": (Kind.EXPENSE, True),
    "Bank Fees": (Kind.EXPENSE, True),
    "Meals (Personal)": (Kind.EXPENSE, False),
    "Personal": (Kind.EXPENSE, False),
    "Refund": (Kind.REFUND, False),
    "Transfer": (Kind.NOT_SPENDING, False),
    "Card Payment": (Kind.NOT_SPENDING, False),
    "Needs Review": (Kind.REVIEW, False),
}

NEEDS_REVIEW = "Needs Review"


def kind_of(category: str) -> Kind:
    return CATEGORIES[category][0]


def is_deductible(category: str) -> bool:
    return CATEGORIES[category][1]
