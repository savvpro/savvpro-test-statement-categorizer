# backend/app/brain/models.py
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from datetime import date

class Category(str, Enum):
    REFUND = "Refund"
    NOT_SPENDING = "Not Spending"
    INCOME = "Income/Payout"
    PLATFORM_FEES = "Platform Fees"
    SHIPPING = "Shipping"
    INVENTORY = "Inventory/Supplies"
    MARKETING = "Marketing"
    SOFTWARE = "Software"
    NEEDS_REVIEW = "Needs Review"

@dataclass
class Transaction:
    date: date
    description: str      # raw
    amount: Decimal       # negative = money out
    normalized: str = ""  # filled by normalizer

@dataclass
class Decision:
    category: Category
    confidence: float     # 0.0–1.0
    reason: str

CONFIDENCE_THRESHOLD = 0.80