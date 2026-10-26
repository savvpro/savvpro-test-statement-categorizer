"""Ordered rule data. The first matching rule wins, so specific rules sit above general ones."""

from dataclasses import dataclass
from typing import Literal

from .schemas import NEEDS_REVIEW

CATEGORIES = (
    "Income",
    "Transfer",
    "Software & Tools",
    "Utilities",
    "Internet & Phone",
    "Rent/Office",
    "Travel & Transport",
    "Entertainment",
    "Food",
    "Groceries",
    "Shopping",
    "Health",
    "Education",
    "Taxes",
    "Bank Fees",
    "Refund",
    "Cash Withdrawal",
    NEEDS_REVIEW,
)


@dataclass(frozen=True)
class Rule:
    kind: Literal["exact", "keyword", "regex"]
    pattern: str
    category: str
    confidence: float
    reason: str
    direction: Literal["debit", "credit"] | None = None
    usd_only: bool = False


def _many(kind, patterns, category, confidence, reason, direction=None) -> list[Rule]:
    return [Rule(kind, p, category, confidence, reason, direction) for p in patterns]


RULES: list[Rule] = [
    # Failed ATM rows and reversals need a partner row; passes.py pairs them.
    Rule(
        "regex",
        r"\b(FAILED|REVERSAL)\b",
        NEEDS_REVIEW,
        0.3,
        "Failed or reversed row without a confirmed pair",
    ),
    # Bank charges sit above cash withdrawal because "WHT ON CASH WDL" contains "CASH WDL".
    Rule(
        "regex",
        r"^(WHT|FED)\b",
        "Bank Fees",
        0.95,
        "Withholding tax or FED charged by the bank",
        "debit",
    ),
    Rule("keyword", "SMS ALERT", "Bank Fees", 0.95, "SMS alert charge", "debit"),
    Rule("exact", "ANNUAL DEBIT CARD FEE", "Bank Fees", 0.95, "Card fee", "debit"),
    Rule("regex", r"\bCARD FEE\b|\bBANK CHARGES\b", "Bank Fees", 0.9, "Bank or card fee", "debit"),
    *_many(
        "keyword",
        ["FBR", "ADVANCE TAX", "INCOME TAX"],
        "Taxes",
        0.95,
        "Tax payment to FBR",
        "debit",
    ),
    # Known ambiguous merchants: refuse to guess.
    Rule(
        "keyword",
        "AMZN MKTP",
        NEEDS_REVIEW,
        0.3,
        "Amazon marketplace: could be tools, shopping or personal",
    ),
    Rule(
        "regex",
        r"(^|\s)M/S\b|\bTRADERS\b",
        NEEDS_REVIEW,
        0.3,
        "Trader or firm payment: purpose unknown",
    ),
    Rule("keyword", "RAAST P2P", NEEDS_REVIEW, 0.3, "Person-to-person transfer: purpose unknown"),
    Rule(
        "keyword", "IBFT", NEEDS_REVIEW, 0.3, "Bank transfer that is not a recognised own account"
    ),
    Rule(
        "keyword",
        "JAZZCASH",
        NEEDS_REVIEW,
        0.3,
        "Wallet top-up: own wallet or someone else is unknown",
    ),
    Rule("keyword", "LIBERTY BOOKS", NEEDS_REVIEW, 0.3, "Bookstore: Education or Shopping unclear"),
    Rule("keyword", "PAYONEER", "Income", 0.95, "Payoneer payout (freelance income)", "credit"),
    Rule("regex", r"\b(ATM )?CASH WDL\b", "Cash Withdrawal", 0.95, "ATM cash withdrawal", "debit"),
    *_many(
        "keyword",
        ["GITHUB", "OPENAI", "NAMECHEAP", "AWS", "FIGMA", "ADOBE", "NOTION", "DIGITALOCEAN"],
        "Software & Tools",
        0.92,
        "Known software or hosting vendor",
        "debit",
    ),
    *_many(
        "keyword",
        ["LESCO", "SNGPL", "SSGC", "WAPDA", "K-ELECTRIC"],
        "Utilities",
        0.95,
        "Utility bill",
        "debit",
    ),
    *_many(
        "keyword",
        ["NAYATEL", "JAZZ MOBILE", "ZONG", "STORMFIBER", "PTCL", "UFONE", "TELENOR"],
        "Internet & Phone",
        0.92,
        "Internet or mobile provider",
        "debit",
    ),
    Rule("keyword", "COWORKING", "Rent/Office", 0.9, "Coworking or office rent", "debit"),
    *_many(
        "keyword",
        ["FOODPANDA", "KFC", "BHATTI CHICKEN", "CAREEM FOOD", "MCDONALDS"],
        "Food",
        0.9,
        "Restaurant or food delivery",
        "debit",
    ),
    Rule("keyword", "NETFLIX", "Entertainment", 0.9, "Streaming subscription", "debit"),
    *_many(
        "keyword",
        ["CAREEM TRIP", "UBER", "PSO FUEL"],
        "Travel & Transport",
        0.85,
        "Ride-hailing or fuel",
        "debit",
    ),
    *_many(
        "keyword",
        ["IMTIAZ", "CARREFOUR", "NAHEED", "AL-FATAH"],
        "Groceries",
        0.9,
        "Supermarket",
        "debit",
    ),
    Rule("keyword", "DARAZ.PK", "Shopping", 0.85, "Online marketplace purchase", "debit"),
    *_many(
        "keyword",
        ["PHARMACY", "HOSPITAL", "CLINIC", "LABORATORY"],
        "Health",
        0.9,
        "Pharmacy or medical",
        "debit",
    ),
    *_many("keyword", ["COURSERA", "UDEMY"], "Education", 0.92, "Online course", "debit"),
    # Last resort: a USD charge from a merchant we do not know is not enough to call it.
    Rule(
        "regex",
        r".",
        "Software & Tools",
        0.5,
        "Unknown foreign (USD) merchant",
        "debit",
        usd_only=True,
    ),
]
