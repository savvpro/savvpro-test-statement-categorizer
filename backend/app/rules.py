"""Keyword tables and settings for the categorizer.

All matching is done on UPPERCASE text. Keep every keyword uppercase.
"""

# Category -> keywords. A row matches a category if any keyword
# appears as a whole word/phrase in the description.
CATEGORIES: dict[str, list[str]] = {
    "Software & Subscriptions": [
        "ADOBE", "FIGMA", "NOTION", "GITHUB", "DROPBOX", "ZOOM", "SLACK",
        "CANVA", "GRAMMARLY",
    ],
    "Travel": [
        "UBER", "LYFT", "DELTA AIR", "UNITED AIR", "AIRBNB", "MARRIOTT",
        "HILTON", "AMTRAK",
    ],
    "Meals (50%)": [
        "STARBUCKS", "CHIPOTLE", "DOORDASH", "GRUBHUB", "RESTAURANT",
    ],
    "Advertising": [
        "GOOGLE ADS", "META ADS", "FACEBK ADS", "LINKEDIN ADS",
    ],
    "Office Supplies": [
        "STAPLES", "OFFICE DEPOT",
    ],
    "Internet & Phone": [
        "COMCAST", "VERIZON", "AT&T", "T-MOBILE",
    ],
    "Professional Services": [
        "LEGALZOOM", "QUICKBOOKS", "ACCOUNTANT", "BOOKKEEPING",
    ],
    "Bank Fees": [
        "MONTHLY FEE", "OVERDRAFT", "SERVICE CHARGE", "WIRE FEE",
    ],
}

# Extra categories the user can pick when fixing a row
# (these have no keyword list: they come from other rules).
EXTRA_CATEGORIES: list[str] = ["Income", "Personal", "Not Spending"]

# Rows that are NOT real spending: transfers, card payments, cash.
NOT_SPENDING: list[str] = [
    "TRANSFER", "PAYMENT THANK YOU", "AUTOPAY", "ONLINE PAYMENT",
    "CREDIT CARD PAYMENT",
]

# Money coming back from a merchant (NOT income).
REFUND_WORDS: list[str] = ["REFUND", "REVERSAL", "RETURN", "CREDIT ADJ"]

# Money in that is real business income.
INCOME_WORDS: list[str] = [
    "STRIPE PAYOUT", "PAYPAL TRANSFER IN", "INVOICE", "CLIENT PAYMENT",
    "DIRECT DEP",
]

# Merchants that sell everything. We never guess these.
AMBIGUOUS: list[str] = [
    "AMAZON", "AMZN", "PAYPAL", "SQ", "SQUARE", "WALMART", "TARGET", "COSTCO",
]

# Below this confidence, a row goes to Needs Review.
CONFIDENCE_THRESHOLD: float = 0.75

# Special labels used across the app.
NEEDS_REVIEW = "Needs Review"
NOT_SPENDING_LABEL = "Not Spending"