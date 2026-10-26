"""The knowledge of the brain: plain data, easy to read and extend.

Everything here is matched against the *normalized* description.
"""
from dataclasses import dataclass

from app.models import Category

IN = "in"    # only applies when money comes in
ANY = "any"


@dataclass(frozen=True)
class Rule:
    category: Category
    keyword: str          # a word or phrase, uppercase
    weight: float         # how strongly this keyword indicates the category
    direction: str = ANY


# --- Special cases: checked first, because they override everything ---------

TRANSFER_PHRASES = ("TRANSFER TO", "TRANSFER FROM", "XFER", "INTERNAL TRANSFER")

SECURITY_DEPOSIT_PHRASES = (
    "SEC DEPOSIT", "SECURITY DEPOSIT", "DEPOSIT REFUND", "DEPOSIT RETURN",
    "RETURN OF DEPOSIT",
)

MORTGAGE_PHRASES = ("MTG", "MORTGAGE", "HOME LOAN")

REFUND_WORDS = ("REFUND", "REVERSAL", "RETURNED")

# Merchants that sell both business and personal things: never guess.
AMBIGUOUS_MERCHANTS = {
    "HOME DEPOT": "sells both repair materials and capital improvements",
    "LOWES": "sells both repair materials and capital improvements",
    "AMAZON": "could be rental supplies or personal shopping",
    "WALMART": "could be rental supplies or personal shopping",
    "TARGET": "could be rental supplies or personal shopping",
    "COSTCO": "could be rental supplies or personal shopping",
}

# --- Keyword rules ----------------------------------------------------------

RULES: tuple[Rule, ...] = (
    # Income: only when money comes IN
    Rule(Category.RENTAL_INCOME, "TENANT", 0.90, IN),
    Rule(Category.RENTAL_INCOME, "RENT", 0.85, IN),
    Rule(Category.RENTAL_INCOME, "RENT PAYMENT", 0.90, IN),
    Rule(Category.RENTAL_INCOME, "ZELLE FROM", 0.55, IN),  # weak: could be anyone
    Rule(Category.RENTAL_INCOME, "VENMO", 0.50, IN),

    Rule(Category.PROPERTY_TAX, "PROPERTY TAX", 0.95),
    Rule(Category.PROPERTY_TAX, "COUNTY TREASURER", 0.85),
    Rule(Category.PROPERTY_TAX, "TAX COLLECTOR", 0.85),

    Rule(Category.INSURANCE, "INSURANCE", 0.90),
    Rule(Category.INSURANCE, "INS PREMIUM", 0.90),
    Rule(Category.INSURANCE, "HOMEOWNERS INS", 0.95),
    Rule(Category.INSURANCE, "STATE FARM", 0.80),
    Rule(Category.INSURANCE, "ALLSTATE", 0.80),

    Rule(Category.UTILITIES, "WATER", 0.85),
    Rule(Category.UTILITIES, "ELECTRIC", 0.85),
    Rule(Category.UTILITIES, "SEWER", 0.85),
    Rule(Category.UTILITIES, "TRASH", 0.85),
    Rule(Category.UTILITIES, "WASTE", 0.80),
    Rule(Category.UTILITIES, "UTILITY", 0.80),
    Rule(Category.UTILITIES, "UTILITIES", 0.80),
    Rule(Category.UTILITIES, "GAS CO", 0.85),

    Rule(Category.REPAIRS, "PLUMBING", 0.90),
    Rule(Category.REPAIRS, "PLUMBER", 0.90),
    Rule(Category.REPAIRS, "ROOFING", 0.90),
    Rule(Category.REPAIRS, "HVAC", 0.90),
    Rule(Category.REPAIRS, "LOCKSMITH", 0.85),
    Rule(Category.REPAIRS, "ELECTRICIAN", 0.90),
    Rule(Category.REPAIRS, "HANDYMAN", 0.90),
    Rule(Category.REPAIRS, "PEST CONTROL", 0.90),
    Rule(Category.REPAIRS, "LANDSCAPING", 0.85),
    Rule(Category.REPAIRS, "REPAIR", 0.80),

    Rule(Category.HOA_FEES, "HOA", 0.95),
    Rule(Category.HOA_FEES, "HOMEOWNERS ASSOCIATION", 0.95),

    Rule(Category.BANK_FEES, "SERVICE FEE", 0.90),
    Rule(Category.BANK_FEES, "MONTHLY FEE", 0.90),
    Rule(Category.BANK_FEES, "MAINTENANCE FEE", 0.90),
    Rule(Category.BANK_FEES, "OVERDRAFT", 0.90),
    Rule(Category.BANK_FEES, "WIRE FEE", 0.90),
    Rule(Category.BANK_FEES, "NSF", 0.85),
)

# Categories that represent money spent (used for refund / direction checks).
EXPENSE_CATEGORIES = frozenset(
    {
        Category.PROPERTY_TAX, Category.INSURANCE, Category.REPAIRS,
        Category.UTILITIES, Category.HOA_FEES, Category.BANK_FEES,
    }
)