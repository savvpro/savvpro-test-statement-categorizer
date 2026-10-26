"""Domain models shared by the parser, the brain and the API."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from decimal import Decimal
from enum import Enum


class Category(str, Enum):
    """Tax-time buckets for a US freelance designer (Schedule C style)."""

    SOFTWARE = "Software & Subscriptions"
    ADVERTISING = "Advertising & Marketing"
    OFFICE = "Office Supplies & Equipment"
    TRAVEL = "Travel"
    MEALS = "Meals (50% deductible)"
    PHONE_INTERNET = "Phone & Internet"
    PROFESSIONAL = "Professional Services"
    EDUCATION = "Education & Training"
    BANK_FEES = "Bank & Card Fees"
    CLIENT_INCOME = "Client Income"
    TRANSFER = "Transfer (not spending)"
    CARD_PAYMENT = "Card Payment (not spending)"
    PERSONAL = "Personal (not deductible)"
    NEEDS_REVIEW = "Needs Review"


# Categories that are not business spending or income; excluded from tax totals.
NON_TAX_CATEGORIES = {Category.TRANSFER, Category.CARD_PAYMENT, Category.PERSONAL}


class Kind(str, Enum):
    DEBIT = "debit"    # money out
    CREDIT = "credit"  # money in


@dataclass
class RawTransaction:
    row_number: int
    date: date
    description: str
    amount: Decimal  # always positive
    kind: Kind


@dataclass
class Decision:
    category: Category
    confidence: float
    reason: str
    is_refund: bool = False
    flags: list[str] = field(default_factory=list)


@dataclass
class Transaction:
    id: str
    row_number: int
    date: date
    description: str
    merchant: str
    amount: Decimal
    kind: Kind
    category: Category
    suggested_category: Category | None
    confidence: float
    reason: str
    is_refund: bool = False
    flags: list[str] = field(default_factory=list)
    user_overridden: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["amount"] = str(self.amount)
        d["kind"] = self.kind.value
        d["category"] = self.category.value
        d["suggested_category"] = self.suggested_category.value if self.suggested_category else None
        return d
