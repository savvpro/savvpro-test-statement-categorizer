"""Shared vocabulary. Money is always an integer number of minor units (cents)."""

from dataclasses import dataclass
from enum import StrEnum


class Category(StrEnum):
    SOFTWARE = "Software"
    TRAVEL = "Travel"
    MEALS = "Meals"
    OFFICE = "Office supplies"
    SERVICES = "Professional services"
    MARKETING = "Marketing"
    FEES = "Bank fees"
    INCOME = "Income"
    TRANSFERS = "Transfers"
    PERSONAL = "Personal"
    REVIEW = "Needs Review"


EXPENSE_CATEGORIES = {
    Category.SOFTWARE,
    Category.TRAVEL,
    Category.MEALS,
    Category.OFFICE,
    Category.SERVICES,
    Category.MARKETING,
    Category.FEES,
}
CURRENCIES = ("USD", "EUR", "GBP", "PKR", "CAD", "AUD")
ENGINE_VERSION = "1.0.0"


class Kind(StrEnum):
    EXPENSE = "expense"
    REFUND = "refund"
    INCOME = "income"
    TRANSFER = "transfer"
    PERSONAL = "personal"
    UNKNOWN = "unknown"


class AmountMode(StrEnum):
    BANK = "bank_signed"
    CARD = "card_signed"
    SPLIT = "debit_credit"


class DateFormat(StrEnum):
    ISO = "iso"
    DMY = "day_first"
    MDY = "month_first"


@dataclass(frozen=True)
class ImportOptions:
    currency: str = "USD"
    amount_mode: AmountMode = AmountMode.BANK
    date_format: DateFormat = DateFormat.ISO


@dataclass(frozen=True)
class ParsedTransaction:
    source_row: int
    date: str
    description: str
    amount_minor: int  # Negative = money out; positive = money in, for every adapter.
    currency: str
    pending: bool = False


@dataclass(frozen=True)
class Decision:
    category: Category
    kind: Kind
    confidence: float  # Fixed rule strength, NOT a calibrated probability.
    rule_id: str
    reason: str
    needs_review: bool = False
