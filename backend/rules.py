"""
Categorization rules for the Statement Categorizer.

Rules are evaluated in strict priority order with direction awareness:
  1. Priority 10: Verified Internal Transfers (between own accounts)
  2. Priority 15: P2P Contractor Payments (Venmo/Zelle to contractor/freelancer)
  3. Priority 20: Refunds & Reversals (Direction-aware: incoming refunds reduce expenses)
  4. Priority 28: Payment Processing Fees (Stripe, PayPal, Square, Merchant fees)
  5. Priority 32: General Bank Fees (Monthly, Overdraft, Interest, Late fees)
  6. Priority 45: Vendor Invoices & Outgoing Payments (Negative amounts)
  7. Priority 50: Verified Client Income (Positive amounts only)
  8. Priority 60–69: Known Expense Categories (Software, Cloud, Ads, Travel, Supplies)
  9. Priority 100: Fallback to Needs Review
"""

from backend.models import TransactionType, BusinessCategory, Confidence

RULES: list[dict] = [
    # -----------------------------------------------------------------------
    # Priority 10 – Verified Internal Transfers (between own accounts)
    # -----------------------------------------------------------------------
    {
        "id": "R001",
        "name": "Transfer between own accounts",
        "priority": 10,
        "patterns": [
            r"transfer to savings\b",
            r"transfer to checking\b",
            r"transfer from checking\b",
            r"transfer from savings\b",
            r"transfer between own accounts\b",
            r"internal transfer\b",
            r"online transfer to (?:savings|checking)\b",
            r"online transfer from (?:savings|checking)\b",
        ],
        "is_regex": True,
        "expected_sign": "any",
        "transaction_type": TransactionType.TRANSFER,
        "business_category": BusinessCategory.INTERNAL_TRANSFER,
        "confidence": Confidence.HIGH,
        "explanation_template": "Verified transfer between own business accounts in '{description}'. Excluded from P&L.",
    },
    {
        "id": "R003",
        "name": "ATM withdrawal",
        "priority": 10,
        "patterns": [
            r"\batm withdrawal\b",
            r"\batm cash\b",
            r"\bcash withdrawal\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.TRANSFER,
        "business_category": BusinessCategory.CASH_WITHDRAWAL,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is a cash withdrawal / owner draw — excluded from operating expenses.",
    },

    # -----------------------------------------------------------------------
    # Priority 15 – P2P Payments with explicit business context
    # -----------------------------------------------------------------------
    {
        "id": "R005",
        "name": "P2P payment to contractor/supplier",
        "priority": 15,
        "patterns": [
            r"venmo.*(?:contractor|freelancer|designer|developer|supplier)",
            r"zelle.*(?:contractor|freelancer|designer|developer|supplier)",
            r"paypal.*(?:contractor|freelancer|designer|developer|supplier)",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.EXPENSE,
        "business_category": BusinessCategory.CONTRACTOR_EXPENSE,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is a contractor/supplier payment made via P2P platform.",
    },

    # -----------------------------------------------------------------------
    # Priority 20 – Refunds (reduce expenses, NOT income)
    # -----------------------------------------------------------------------
    {
        "id": "R010",
        "name": "Refund / Credit Adjustment",
        "priority": 20,
        "patterns": [
            r"\brefund\b",
            r"\breversal\b",
            r"\bcredit adj(?:ustment)?\b",
            r"\bchargeback won\b",
        ],
        "is_regex": True,
        "expected_sign": "positive",
        "transaction_type": TransactionType.REFUND,
        "business_category": BusinessCategory.UNKNOWN,  # Refined by categorizer
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is a refund/reversal. Handled as expense reduction, not operating revenue.",
    },

    # -----------------------------------------------------------------------
    # Priority 28 – Specific Payment Processing Fees (BEFORE general bank fees)
    # -----------------------------------------------------------------------
    {
        "id": "R025",
        "name": "Payment processing fees",
        "priority": 28,
        "patterns": [
            r"stripe(?:\s+processing)?\s+fee\b",
            r"paypal(?:\s+transaction)?\s+fee\b",
            r"square(?:\s+processing)?\s+fee\b",
            r"merchant(?:\s+processing)?\s+fee\b",
            r"shopify(?:\s+payments)?\s+fee\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.FEE,
        "business_category": BusinessCategory.PAYMENT_PROCESSING,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is a payment gateway processing fee.",
    },

    # -----------------------------------------------------------------------
    # Priority 32 – General Bank Fees
    # -----------------------------------------------------------------------
    {
        "id": "R020",
        "name": "Bank service & maintenance fees",
        "priority": 32,
        "patterns": [
            r"\bmonthly\s+(?:service\s+)?fee\b",
            r"\bannual\s+fee\b",
            r"\binterest\s+charge\b",
            r"\blate\s+(?:payment\s+)?fee\b",
            r"\boverdraft\s+fee\b",
            r"\bwire\s+(?:transfer\s+)?fee\b",
            r"\bservice\s+charge\b",
            r"\baccount\s+maintenance\s+fee\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.FEE,
        "business_category": BusinessCategory.BANK_FEES,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is a bank or account maintenance fee.",
    },

    # -----------------------------------------------------------------------
    # Priority 45 – Outgoing Vendor Invoices / Payments
    # -----------------------------------------------------------------------
    {
        "id": "R028",
        "name": "Vendor invoice payment",
        "priority": 45,
        "patterns": [
            r"invoice\s+from\s+vendor\b",
            r"invoice\s+payment\s+to\b",
            r"vendor\s+invoice\b",
            r"supplier\s+invoice\b",
            r"bill\s+payment\s+to\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.EXPENSE,
        "business_category": BusinessCategory.GENERAL_EXPENSE,
        "confidence": Confidence.MEDIUM,
        "explanation_template": "'{description}' is an outgoing vendor/supplier invoice payment.",
    },

    # -----------------------------------------------------------------------
    # Priority 50 – Known Client Income (Positive amounts only)
    # -----------------------------------------------------------------------
    {
        "id": "R030",
        "name": "Client payment / incoming invoice",
        "priority": 50,
        "patterns": [
            r"client\s+payment\b",
            r"payment\s+received\b",
            r"acme\s+corp.*invoice\b",
            r"acme\s+corp\b",
            r"paypal\s+\*freelande",
            r"webflow\s+project\b",
            r"customer\s+deposit\b",
            r"client\s+retainer\b",
        ],
        "is_regex": True,
        "expected_sign": "positive",
        "transaction_type": TransactionType.INCOME,
        "business_category": BusinessCategory.CLIENT_INCOME,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is incoming client revenue.",
    },

    # -----------------------------------------------------------------------
    # Priority 60–69 – Known Expense Categories (Negative amounts expected)
    # -----------------------------------------------------------------------
    {
        "id": "R040",
        "name": "Software subscriptions",
        "priority": 60,
        "patterns": [
            r"\badobe(?:\s+creative)?\b",
            r"\bfigma\b",
            r"\bcanva\b",
            r"\bnotion\b",
            r"\bslack\b",
            r"\bgithub\b",
            r"\bwix\b",
            r"\bsquarespace\b",
            r"\bdropbox\b",
            r"\bzoom\b",
            r"\bmicrosoft\s+365\b",
            r"\bgoogle\s+workspace\b",
            r"\bjetbrains\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.EXPENSE,
        "business_category": BusinessCategory.SOFTWARE,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is a recognized software subscription.",
    },
    {
        "id": "R041",
        "name": "Cloud infrastructure & hosting",
        "priority": 60,
        "patterns": [
            r"\bamazon\s+web\s+services\b",
            r"\baws\b",  # with word boundaries \b to avoid matching 'flaws', 'lawson'
            r"\bgoogle\s+cloud\b",
            r"\bazure\b",
            r"\bdigitalocean\b",
            r"\bheroku\b",
            r"\bvercel\b",
            r"\bnetlify\b",
            r"\bcloudflare\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.EXPENSE,
        "business_category": BusinessCategory.SOFTWARE,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is cloud infrastructure hosting.",
    },
    {
        "id": "R042",
        "name": "Digital advertising",
        "priority": 61,
        "patterns": [
            r"\bgoogle\s+ads\b",
            r"\bfacebook\s+ads\b",
            r"\bmeta\s+ads\b",
            r"\blinkedin\s+ads\b",
            r"\btwitter\s+ads\b",
            r"\binstagram\s+ads\b",
            r"\btiktok\s+ads\b",
            r"\bbing\s+ads\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.EXPENSE,
        "business_category": BusinessCategory.ADVERTISING,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is advertising spend.",
    },
    {
        "id": "R043",
        "name": "Office supplies & equipment",
        "priority": 62,
        "patterns": [
            r"\bstaples\b",
            r"\boffice\s+depot\b",
            r"\bofficeworks\b",
            r"\bpaper\s+source\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.EXPENSE,
        "business_category": BusinessCategory.OFFICE_SUPPLIES,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is an office supplies purchase.",
    },
    {
        "id": "R044",
        "name": "Travel & transportation",
        "priority": 63,
        "patterns": [
            r"\buber\b",
            r"\blyft\b",
            r"\bdelta\s+air\b",
            r"\bunited\s+air\b",
            r"\bsouthwest\b",
            r"\bamerican\s+air\b",
            r"\bjetblue\b",
            r"\bspirit\s+air\b",
            r"\bamtrak\b",
            r"\btaxi\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.EXPENSE,
        "business_category": BusinessCategory.TRAVEL,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is a business travel expense.",
    },
    {
        "id": "R045",
        "name": "Lodging & accommodation",
        "priority": 63,
        "patterns": [
            r"\bmarriott\b",
            r"\bhilton\b",
            r"\bhyatt\b",
            r"\bairbnb\b",
            r"\bhotel\b",
            r"\bbooking\.com\b",
            r"\bexpedia\b",
        ],
        "is_regex": True,
        "expected_sign": "negative",
        "transaction_type": TransactionType.EXPENSE,
        "business_category": BusinessCategory.ACCOMMODATION,
        "confidence": Confidence.HIGH,
        "explanation_template": "'{description}' is a lodging/accommodation expense.",
    },
]

# The fallback rule applied when nothing else matches
FALLBACK_RULE = {
    "id": "R999",
    "name": "Unknown / Needs Review",
    "priority": 100,
}
