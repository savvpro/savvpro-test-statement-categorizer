import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

TAX_CATEGORIES = {
    "Software & Subscriptions": [
        "ADOBE", "FIGMA", "GITHUB", "GITLAB", "JETBRAINS", "AWS", "AMAZON WEB SERVICES",
        "DIGITALOCEAN", "NOTION", "VERCEL", "SLACK", "OPENAI", "ANTHROPIC", "CANVA",
        "1PASSWORD", "LASTPASS", "ZOOM", "DROPBOX", "MICROSOFT 365", "MSFT", "ATLASSIAN",
        "JIRA", "TRELLO", "HEROKU", "SUPABASE", "ENVATO", "SHUTTERSTOCK", "MIDJOURNEY",
    ],
    "Travel & Transit": [
        "UBER", "LYFT", "TAXI", "CAB", "AIRLINE", "DELTA", "UNITED AIRLINES",
        "AMERICAN AIR", "SOUTHWEST", "HOTEL", "MARRIOTT", "HILTON", "AIRBNB",
        "AMTRAK", "TRAIN", "MTA", "BART", "PARKING", "TOLL",
    ],
    "Meals (50% Deductible)": [
        "STARBUCKS", "COSTA COFFEE", "BLUE BOTTLE", "PEETS", "DUNKIN", "PRET A MANGER",
        "DOORDASH", "GRUBHUB", "UBER EATS", "SWEETGREEN", "CHIPOTLE", "PANERA",
    ],
    "Office Supplies & Equipment": [
        "STAPLES", "OFFICE DEPOT", "BEST BUY", "APPLE STORE", "APPLE.COM/BILL",
        "MICRO CENTER", "LOGITECH", "KEYCHRON", "PRINTER", "INK", "STATIONERY",
    ],
    "Advertising & Marketing": [
        "GOOGLE ADS", "FACEBOOK ADS", "META ADS", "LINKEDIN ADS", "TWITTER ADS",
        "X ADS", "MAILCHIMP", "CONVERTKIT", "SUBSTACK", "INSTAGRAM ADS", "TIKTOK ADS",
    ],
    "Utilities & Internet": [
        "COMCAST", "XFINITY", "VERIZON", "AT&T", "SPECTRUM", "CHARTER",
        "T-MOBILE", "ELECTRIC", "WATER BILL", "CON EDISON", "INTERNET", "FIBER",
    ],
    "Banking & Processing Fees": [
        "STRIPE FEE", "PAYPAL FEE", "WIRE FEE", "OVERDRAFT FEE", "MONTHLY SERVICE FEE",
        "BANK FEE", "FOREIGN TRANSACTION FEE", "ACCOUNT MAINTENANCE FEE",
    ],
    "Contract Labor & Professional Services": [
        "UPWORK FREELANCER", "FIVERR GIG", "LEGALZOOM", "CPA", "ACCOUNTING",
        "TAX PREP", "ATTORNEY", "LAWYER", "BOOKKEEPING",
    ],
}

TRANSFER_KEYWORDS = [
    "TRANSFER TO SAVINGS",
    "TRANSFER FROM SAVINGS",
    "INTERNAL TRANSFER",
    "PAYMENT TO OWN ACCOUNT",
    "CREDIT CARD PAYMENT",
    "AUTOPAY PAYMENT",
    "ONLINE PAYMENT THANK YOU",
    "TRANSFER TO CHECKING",
    "TRANSFER FROM CHECKING",
    "ATM WITHDRAWAL",
]

INCOME_KEYWORDS = [
    "CLIENT PAYMENT",
    "INVOICE PAYMENT",
    "STRIPE PAYOUT",
    "UPWORK ESCROW",
    "DIRECT DEPOSIT",
    "CLIENT DEPOSIT",
    "WIRE TRANSFER CREDIT",
    "CONSULTING FEE",
    "PAYPAL PAYOUT",
]

REFUND_INDICATORS = [
    "REFUND",
    "REVERSAL",
    "RETURN",
    "CHARGEBACK REVERSED",
    "CREDIT ADJ",
    "DISPUTE WON",
]


def clean_description(desc: str) -> str:
    """Normalize raw bank statement description."""
    if not desc:
        return ""
    text = desc.upper().strip()
    text = re.sub(r"[\*#\-_/\\:]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_amount(raw_amount: Any) -> Optional[Decimal]:
    """
    Parse a numeric amount safely from strings, floats, ints, or accounting formats.
    e.g. '(12.50)' -> -12.50, '$1,200.00' -> 1200.00
    """
    if raw_amount is None:
        return None

    str_val = str(raw_amount).strip()
    if not str_val:
        return None

    # Handle accounting negative format: (123.45) -> -123.45
    is_paren_negative = False
    if str_val.startswith("(") and str_val.endswith(")"):
        is_paren_negative = True
        str_val = str_val[1:-1].strip()

    str_val = str_val.replace("$", "").replace("USD", "").replace(",", "").strip()

    try:
        val = Decimal(str_val)
        if is_paren_negative and val > 0:
            val = -val
        if not val.is_finite():
            return None
        return val
    except (InvalidOperation, ValueError):
        return None


def match_rules(text: str) -> List[str]:
    """Find tax categories matching any keyword in the cleaned text."""
    matches = []
    for category, keywords in TAX_CATEGORIES.items():
        for keyword in keywords:
            pattern = r"(^|\b|\s)" + re.escape(keyword) + r"(\b|\s|$)"
            if re.search(pattern, text):
                matches.append(category)
                break
    return matches


def categorize_transaction(description: str, amount: Any) -> Dict[str, Any]:
    """
    The Brain: Pure deterministic, rule-based decision engine.
    Never hallucinates, never calls external AI models, and explicitly flags
    'Needs Review' whenever uncertain.
    """
    merchant = clean_description(description)
    val = parse_amount(amount)

    if val is None or not merchant:
        return {
            "category": "Needs Review",
            "confidence": "low",
            "reason": "Missing or malformed transaction description or amount.",
            "transaction_type": "unknown",
            "include_in_expenses": False,
            "is_tax_deductible": False,
        }

    # 1. Internal Transfers & Non-expense movements
    if any(term in merchant for term in TRANSFER_KEYWORDS):
        return {
            "category": "Transfer",
            "confidence": "high",
            "reason": "Internal transfer or credit card repayment. Excluded from tax deductions.",
            "transaction_type": "transfer",
            "include_in_expenses": False,
            "is_tax_deductible": False,
        }

    # 2. Refunds and Reversals
    is_refund = any(ind in merchant for ind in REFUND_INDICATORS)
    if is_refund:
        matched_categories = match_rules(merchant)
        if len(matched_categories) == 1:
            category = matched_categories[0]
            return {
                "category": category,
                "confidence": "high",
                "reason": f"Refund/reversal matching {category}. Offsets original expense.",
                "transaction_type": "refund",
                "include_in_expenses": False,
                "is_tax_deductible": False,
            }
        return {
            "category": "Needs Review",
            "confidence": "low",
            "reason": "Refund detected, but original merchant category could not be resolved with certainty.",
            "transaction_type": "refund",
            "include_in_expenses": False,
            "is_tax_deductible": False,
        }

    # 3. Positive amounts (Incoming Money / Deposits)
    if val > 0:
        if any(term in merchant for term in INCOME_KEYWORDS):
            return {
                "category": "Client Revenue",
                "confidence": "high",
                "reason": "Recognized client invoice or platform payout. Counted as taxable gross income.",
                "transaction_type": "income",
                "include_in_expenses": False,
                "is_tax_deductible": False,
            }
        return {
            "category": "Needs Review",
            "confidence": "low",
            "reason": "Incoming deposit detected. Verify if client income, personal capital injection, or reimbursement.",
            "transaction_type": "deposit",
            "include_in_expenses": False,
            "is_tax_deductible": False,
        }

    # 4. Outgoing Money (Expenses / Outflows: val <= 0)
    matched_categories = match_rules(merchant)

    if len(matched_categories) == 1:
        category = matched_categories[0]
        return {
            "category": category,
            "confidence": "high",
            "reason": f"Matched verified merchant keywords for '{category}'.",
            "transaction_type": "expense",
            "include_in_expenses": True,
            "is_tax_deductible": True,
        }

    if len(matched_categories) > 1:
        return {
            "category": "Needs Review",
            "confidence": "low",
            "reason": f"Ambiguous transaction: matches multiple categories ({', '.join(matched_categories)}).",
            "transaction_type": "expense",
            "include_in_expenses": False,
            "is_tax_deductible": False,
        }

    # 5. Fallback: Unknown merchant
    return {
        "category": "Needs Review",
        "confidence": "low",
        "reason": "Unrecognized merchant or generic description. Requires user review for tax classification.",
        "transaction_type": "expense",
        "include_in_expenses": False,
        "is_tax_deductible": False,
    }
