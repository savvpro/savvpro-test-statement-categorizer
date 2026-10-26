"""
Deterministic Transaction Categorization Engine.

Rule-based categorization for freelancers preparing financial statements for tax time.
No external network calls, LLMs, or paid APIs are used.
Every decision provides an audit trail explaining the matched rule.
"""

import re
from typing import NamedTuple, Optional
from .models import Category, TransactionStatus


class Decision(NamedTuple):
    category: Category
    confidence: float
    status: TransactionStatus
    matched_rule: str


# Rule Definitions
TRANSFER_PATTERNS = [
    r"\btransfer\s+to\b",
    r"\btransfer\s+from\b",
    r"\bwire\s+transfer\b",
    r"\bach\s+transfer\b",
    r"\binternal\s+transfer\b",
    r"\btfr\s+(to|from)\b",
    r"\bzelle\s+transfer\b",
    r"\be-transfer\b",
    r"\bonline\s+transfer\b",
    r"\btransfer\s+to\s+savings\b",
    r"\btransfer\s+to\s+checking\b",
    r"\baccount\s+transfer\b",
    r"\bfunds\s+transfer\b",
]

REFUND_PATTERNS = [
    r"\brefund\b",
    r"\breversal\b",
    r"\bcashback\b",
    r"\breturned\s+item\b",
    r"\bcharge\s+reversal\b",
    r"\bcredit\s+adjustment\b",
    r"\bmerchant\s+refund\b",
    r"\bdispute\s+credit\b",
]

INCOME_PATTERNS = [
    r"\bclient\s+payment\b",
    r"\binvoice\s+paid\b",
    r"\bstripe\s+payout\b",
    r"\bpaypal\s+deposit\b",
    r"\bupwork\s+escrow\b",
    r"\bfiverr\s+payout\b",
    r"\bdirect\s+deposit\b",
    r"\bconsulting\s+fee\b",
    r"\bretainer\s+fee\b",
    r"\bsquare\s+deposit\b",
    r"\bmerchant\s+settlement\b",
    r"\bwire\s+credit\b",
    r"\bpayroll\s+credit\b",
    r"\bdividend\b",
    r"\binterest\s+earned\b",
]

SOFTWARE_KEYWORDS = [
    "adobe", "creative cloud", "figma", "github", "gitlab", "aws", "amazon web services",
    "google cloud", "gcp", "digitalocean", "heroku", "jetbrains", "atlassian", "jira",
    "slack", "zoom", "notion", "linear", "vercel", "netlify", "openai", "anthropic",
    "chatgpt", "canva", "loom", "1password", "lastpass", "dropbox", "google workspace",
    "microsoft 365", "office 365", "sublime", "cursor", "datadog", "sentry", "twilio",
    "sendgrid", "mailchimp", "docker", "postman", "miro", "airtable", "salesforce", "hubspot"
]

TRAVEL_KEYWORDS = [
    "uber", "lyft", "delta", "delta air", "delta airlines", "american airlines", "united airlines",
    "southwest", "amtrak", "trainline", "expedia", "airbnb", "booking.com", "marriott", "hilton",
    "hyatt", "hotel", "car rental", "hertz", "enterprise rent-a-car", "avis", "budget rent",
    "shell oil", "chevron", "exxon", "bp gas", "mobil", "parking", "tollway", "ezpass",
    "flight", "airline", "airlines", "cab", "taxi"
]

MEALS_KEYWORDS = [
    "starbucks", "dunkin", "mcdonald", "subway", "chipotle", "sweetgreen", "panera",
    "door dash", "doordash", "uber eats", "grubhub", "cava", "shake shack", "restaurant",
    "cafe", "café", "bistro", "diner", "coffee", "pizza", "bakery", "burger", "sushi",
    "bar & grill", "tacos"
]

OFFICE_SUPPLIES_KEYWORDS = [
    "staples", "office depot", "best buy", "apple store", "b&h photo", "micro center",
    "officemax", "ikea", "paper", "printer ink", "cartridge", "desk", "office chair",
    "hardware store", "homedepot", "lowes"
]

OTHER_BUSINESS_EXPENSE_KEYWORDS = [
    "usps", "fedex", "ups store", "postage", "legalzoom", "accountant", "cpa fee",
    "bookkeeper", "bank fee", "monthly maintenance fee", "annual fee", "domain renewal",
    "godaddy", "namecheap", "advertising", "facebook ads", "google ads", "linkedin ads",
    "insurance", "co-working", "wework", "regus"
]

# Ambiguous multi-category vendors that freelancers frequently use for both personal and business
AMBIGUOUS_VENDORS = [
    "amazon", "amzn", "target", "walmart", "costco", "walgreens", "cvs", "ebay"
]


def clean_description(desc: str) -> str:
    """Normalize raw description text for consistent rule matching."""
    if not desc:
        return ""
    # Lowercase and replace asterisks, underscores, hyphens, and multiple spaces
    cleaned = desc.lower()
    cleaned = re.sub(r"[\*\_#\-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def categorize_transaction(description: str, amount: float) -> Decision:
    """
    Categorizes a transaction based on description, amount, and business logic.
    
    Amount convention:
      - Negative (< 0): Outflow / Debit / Spending
      - Positive (> 0): Inflow / Credit / Deposit / Refund
    """
    cleaned = clean_description(description)

    # 1. Blank or uninformative description
    if not cleaned or cleaned in ["none", "null", "n/a", "unknown", "transaction"]:
        return Decision(
            category=Category.NEEDS_REVIEW,
            confidence=0.0,
            status=TransactionStatus.NEEDS_REVIEW,
            matched_rule="Blank or uninformative description requires manual review"
        )

    # 2. Transfers (Must be checked before expenses and income)
    for pattern in TRANSFER_PATTERNS:
        if re.search(pattern, cleaned):
            return Decision(
                category=Category.TRANSFER,
                confidence=0.95,
                status=TransactionStatus.CATEGORIZED,
                matched_rule=f"Transfer pattern matched ('{pattern}'). Excluded from business expenses and income."
            )

    # 3. Refunds & Reversals (Crucial: a refund must never be counted as income)
    is_positive = amount > 0
    for pattern in REFUND_PATTERNS:
        if re.search(pattern, cleaned):
            return Decision(
                category=Category.REFUND,
                confidence=0.95,
                status=TransactionStatus.CATEGORIZED,
                matched_rule=f"Refund indicator matched ('{pattern}'). Offsets expenses; not taxable income."
            )

    # 4. Inflows / Positive Amounts
    if is_positive:
        # Check if matching known income keywords
        for pattern in INCOME_PATTERNS:
            if re.search(pattern, cleaned):
                return Decision(
                    category=Category.INCOME,
                    confidence=0.95,
                    status=TransactionStatus.CATEGORIZED,
                    matched_rule=f"Business revenue pattern matched ('{pattern}')."
                )
        
        # If an inflow does not match known income or refund patterns,
        # it is ambiguous (e.g. unknown deposit, personal gift, or unrecognized refund).
        return Decision(
            category=Category.NEEDS_REVIEW,
            confidence=0.30,
            status=TransactionStatus.NEEDS_REVIEW,
            matched_rule=f"Unrecognized deposit/inflow (+${amount:.2f}). Needs manual classification (Income vs. Refund vs. Capital)."
        )

    # 5. Outflows / Spending Categories

    # 5a. Software Subscriptions
    for kw in SOFTWARE_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
            return Decision(
                category=Category.SOFTWARE,
                confidence=0.95,
                status=TransactionStatus.CATEGORIZED,
                matched_rule=f"Software vendor matched ('{kw}')."
            )

    # 5b. Travel & Transportation
    for kw in TRAVEL_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
            return Decision(
                category=Category.TRAVEL,
                confidence=0.92,
                status=TransactionStatus.CATEGORIZED,
                matched_rule=f"Travel/transportation provider matched ('{kw}')."
            )

    # 5c. Meals & Dining
    for kw in MEALS_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
            return Decision(
                category=Category.MEALS,
                confidence=0.90,
                status=TransactionStatus.CATEGORIZED,
                matched_rule=f"Meals & dining vendor matched ('{kw}')."
            )

    # 5d. Office Supplies & Equipment
    for kw in OFFICE_SUPPLIES_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
            return Decision(
                category=Category.OFFICE_SUPPLIES,
                confidence=0.90,
                status=TransactionStatus.CATEGORIZED,
                matched_rule=f"Office supplies vendor matched ('{kw}')."
            )

    # 5e. Other Business Expenses (Shipping, professional services, banking fees)
    for kw in OTHER_BUSINESS_EXPENSE_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
            return Decision(
                category=Category.OTHER_BUSINESS_EXPENSE,
                confidence=0.85,
                status=TransactionStatus.CATEGORIZED,
                matched_rule=f"General business expense matched ('{kw}')."
            )

    # 5f. Ambiguous Big-Box Retailers (e.g. Amazon, Target, Walmart)
    for vendor in AMBIGUOUS_VENDORS:
        if re.search(r"\b" + re.escape(vendor) + r"\b", cleaned):
            return Decision(
                category=Category.NEEDS_REVIEW,
                confidence=0.40,
                status=TransactionStatus.NEEDS_REVIEW,
                matched_rule=f"Multi-purpose vendor matched ('{vendor}'). Requires manual confirmation for tax-deductible status."
            )

    # 6. Fallback: Unknown description
    return Decision(
        category=Category.NEEDS_REVIEW,
        confidence=0.10,
        status=TransactionStatus.NEEDS_REVIEW,
        matched_rule="Unrecognized merchant or description; manual review recommended."
    )
