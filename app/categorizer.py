import re
from decimal import Decimal

CATEGORIES = (
    "Income",
    "Groceries",
    "Dining",
    "Transport",
    "Shopping",
    "Bills",
    "Healthcare",
    "Transfers",
    "Software",
    "Other",
    "Needs Review",
)

_CATEGORY_RULES = (
    (
        "Groceries",
        (
            "WHOLE FOODS",
            "TRADER JOE",
            "SAFEWAY",
            "KROGER",
            "ALDI",
            "PUBLIX",
            "GROCERY",
            "SUPERMARKET",
            "COSTCO",
        ),
    ),
    (
        "Dining",
        (
            "RESTAURANT",
            "STARBUCKS",
            "MCDONALD",
            "CHIPOTLE",
            "DOORDASH",
            "GRUBHUB",
            "UBER EATS",
            "PANERA",
            "SUBWAY",
            "PIZZA",
            "TACO BELL",
        ),
    ),
    (
        "Transport",
        (
            "UBER TRIP",
            "LYFT",
            "SHELL",
            "CHEVRON",
            "EXXON",
            "BP ",
            "PARKING",
            "TRANSIT",
            "METRO",
            "TOLL",
            "AIRLINE",
            "AMTRAK",
            "GAS STATION",
        ),
    ),
    (
        "Shopping",
        (
            "AMAZON",
            "TARGET",
            "WALMART",
            "BEST BUY",
            "EBAY",
            "ETSY",
            "IKEA",
            "HOME DEPOT",
            "LOWE'S",
            "NIKE",
        ),
    ),
    (
        "Bills",
        (
            "ELECTRIC",
            "UTILITY",
            "WATER BILL",
            "INTERNET",
            "COMCAST",
            "VERIZON",
            "AT&T",
            "PHONE BILL",
            "INSURANCE",
            "RENT",
            "MORTGAGE",
            "NETFLIX",
            "SPOTIFY",
        ),
    ),
    (
        "Healthcare",
        (
            "HOSPITAL",
            "MEDICAL",
            "DENTAL",
            "DENTIST",
            "PHARMACY",
            "CVS",
            "WALGREENS",
            "HEALTH CLINIC",
        ),
    ),
    (
        "Software",
        ("ADOBE", "MICROSOFT 365", "GITHUB", "FIGMA", "CANVA", "NOTION"),
    ),
    (
        "Other",
        ("BANK FEE", "OVERDRAFT FEE", "USPS", "POST OFFICE", "DONATION", "CHARITY"),
    ),
)

_TRANSFER_RE = re.compile(
    r"\b(?:TRANSFER|XFER)\b|\bMOVE MONEY\b|\bFROM SAVINGS\b|\bTO SAVINGS\b",
    re.IGNORECASE,
)
_REFUND_RE = re.compile(
    r"\b(?:REFUND(?:ED)?|RETURN(?:ED)?|REVERSAL|MERCHANT CREDIT|CREDIT ADJUSTMENT|PURCHASE CREDIT)\b",
    re.IGNORECASE,
)
_INCOME_RE = re.compile(
    r"\b(?:PAYROLL|DIRECT DEPOSIT|SALARY|CLIENT PAYMENT|INVOICE PAID|"
    r"FREELANCE PAYMENT|INTEREST CREDIT)\b",
    re.IGNORECASE,
)


def _merchant_category(description: str) -> str | None:
    normalized = f" {description.upper()} "
    for category, keywords in _CATEGORY_RULES:
        if any(f" {keyword.strip()} " in normalized for keyword in keywords):
            return category
    return None


def categorize_transaction(
    description: str, amount: Decimal
) -> tuple[str, str, bool, str | None]:
    """Return category, transaction type, review flag, and review reason."""
    if _TRANSFER_RE.search(description):
        return "Transfers", "transfer", False, None

    if _REFUND_RE.search(description):
        merchant_description = _REFUND_RE.sub(" ", description)
        category = _merchant_category(merchant_description)
        if category is None:
            return (
                "Needs Review",
                "refund",
                True,
                "Refund detected, but the original purchase category is unknown.",
            )
        return category, "refund", False, None

    if _INCOME_RE.search(description):
        return "Income", "income", False, None

    category = _merchant_category(description)
    if category is not None:
        return category, "purchase", False, None

    return (
        "Needs Review",
        "unknown",
        True,
        "No categorization rule matched this transaction.",
    )
