"""Central constants for the categorization brain.

All thresholds, weights, and keyword lists live here so they are easy to
audit and tune. No magic numbers should be scattered elsewhere.
"""

# --- Confidence values ---
CONFIDENCE_EXACT = 0.95      # Exact merchant name match
CONFIDENCE_KEYWORD = 0.80    # Keyword/contains merchant match
CONFIDENCE_OVERRIDE = 1.00   # User-provided override
CONFIDENCE_STRUCTURAL = 0.98 # Structural rules (transfer, refund, income)

# --- Thresholds ---
CONFIDENCE_MIN = 0.70        # Below this => Needs Review
CONFIDENCE_GAP_MAX = 0.10    # If top-2 gap is smaller => Needs Review

# --- Structural rule keywords ---
TRANSFER_KEYWORDS = [
    "TRANSFER TO", "TRANSFER FROM",
    "PAYMENT THANK YOU",
    "AUTOPAY",
    "CARD PAYMENT",
]

REFUND_KEYWORDS = ["REFUND", "REVERSAL"]

INCOME_KEYWORDS = ["INVOICE", "PAYROLL", "DEPOSIT", "CLIENT"]

# --- Noisy prefixes stripped during normalization ---
NOISY_PREFIXES = [
    "SQ *", "SQ*",
    "TST*",
    "AMZN MKTP US*", "AMZN MKTP US",
    "POS ",
    "PURCHASE ",
    "PAYPAL *", "PAYPAL*",
]

# --- Categories excluded from spending totals ---
NON_SPENDING_CATEGORIES = {"Transfer"}

# --- Categories shown as negative spend in summary ---
REFUND_CATEGORIES = {"Refund"}
