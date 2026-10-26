"""
Schedule C categories with metadata.

Every category carries:
 - schedule_c_line: the IRS Schedule C line reference (if applicable)
 - deductible_pct: default deductible percentage (100 unless noted)
 - cat_type: income | expense | excluded | review
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    EXCLUDED = "excluded"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class CategoryMeta:
    label: str
    cat_type: CategoryType
    schedule_c_line: str
    deductible_pct: int = 100  # percentage as integer (50 for meals)


# ── Master category registry ────────────────────────────────────────────────
CATEGORIES: dict[str, CategoryMeta] = {
    # Income
    "business_income": CategoryMeta(
        "Business Income", CategoryType.INCOME, "Line 1",
    ),
    "refund_reimbursement": CategoryMeta(
        "Refund or Reimbursement", CategoryType.INCOME, "N/A (nets against expense)",
        deductible_pct=0,
    ),
    # Expenses
    "advertising": CategoryMeta(
        "Advertising", CategoryType.EXPENSE, "Line 8",
    ),
    "software_subscriptions": CategoryMeta(
        "Software and Subscriptions", CategoryType.EXPENSE, "Line 18 (Other)",
    ),
    "office_supplies": CategoryMeta(
        "Office Supplies", CategoryType.EXPENSE, "Line 18 (Other)",
    ),
    "travel": CategoryMeta(
        "Travel", CategoryType.EXPENSE, "Line 24a",
    ),
    "meals": CategoryMeta(
        "Meals", CategoryType.EXPENSE, "Line 24b",
        deductible_pct=50,
    ),
    "vehicle": CategoryMeta(
        "Vehicle", CategoryType.EXPENSE, "Line 9",
    ),
    "contract_labor": CategoryMeta(
        "Contract Labor", CategoryType.EXPENSE, "Line 11",
    ),
    "professional_services": CategoryMeta(
        "Professional Services", CategoryType.EXPENSE, "Line 17",
    ),
    "insurance": CategoryMeta(
        "Insurance", CategoryType.EXPENSE, "Line 15",
    ),
    "rent_utilities": CategoryMeta(
        "Rent and Utilities", CategoryType.EXPENSE, "Lines 20b, 25",
    ),
    "bank_processing_fees": CategoryMeta(
        "Bank and Processing Fees", CategoryType.EXPENSE, "Line 18 (Other)",
    ),
    "education": CategoryMeta(
        "Education", CategoryType.EXPENSE, "Line 18 (Other)",
    ),
    "equipment": CategoryMeta(
        "Equipment", CategoryType.EXPENSE, "Line 13 (Depreciation)",
    ),
    "taxes_licenses": CategoryMeta(
        "Taxes and Licenses", CategoryType.EXPENSE, "Line 23",
    ),
    # Not spending (excluded)
    "transfer": CategoryMeta(
        "Transfer", CategoryType.EXCLUDED, "N/A",
        deductible_pct=0,
    ),
    "credit_card_payment": CategoryMeta(
        "Credit Card Payment", CategoryType.EXCLUDED, "N/A",
        deductible_pct=0,
    ),
    "owner_draw_contribution": CategoryMeta(
        "Owner Draw or Contribution", CategoryType.EXCLUDED, "N/A",
        deductible_pct=0,
    ),
    "personal": CategoryMeta(
        "Personal", CategoryType.EXCLUDED, "N/A",
        deductible_pct=0,
    ),
    # Fallback
    "needs_review": CategoryMeta(
        "Needs Review", CategoryType.REVIEW, "N/A",
        deductible_pct=0,
    ),
}

# Quick look-ups
CATEGORY_KEYS = list(CATEGORIES.keys())
EXPENSE_KEYS = [k for k, v in CATEGORIES.items() if v.cat_type == CategoryType.EXPENSE]
INCOME_KEYS = [k for k, v in CATEGORIES.items() if v.cat_type == CategoryType.INCOME]
EXCLUDED_KEYS = [k for k, v in CATEGORIES.items() if v.cat_type == CategoryType.EXCLUDED]


def get_deductible_pct(category: str) -> int:
    """Return the deductible percentage for a category key."""
    meta = CATEGORIES.get(category)
    return meta.deductible_pct if meta else 0
