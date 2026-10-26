"""
Deterministic rules-based categorization engine for Freelance Ledger.
NO LLM or AI model is used at runtime. All categorization follows explicit,
auditable, layered deterministic heuristics with explainability and confidence scoring.
"""

import re
from decimal import Decimal

# Known exact or prefix merchant mappings (Layer 1: Exact / Canonical Merchants)
MERCHANT_EXACT_RULES = {
    # Software & Subscriptions
    "ADOBE": ("Software", 0.98, "Matched verified SaaS vendor: Adobe"),
    "ADBE": ("Software", 0.98, "Matched verified SaaS vendor: Adobe"),
    "ADBE*CREATIVECLOUD": ("Software", 0.98, "Matched verified SaaS vendor: Adobe Creative Cloud"),
    "FIGMA": ("Software", 0.98, "Matched design software vendor: Figma"),
    "GITHUB": ("Software", 0.98, "Matched developer tooling vendor: GitHub"),
    "JETBRAINS": ("Software", 0.98, "Matched developer tooling vendor: JetBrains"),
    "CANVA": ("Software", 0.98, "Matched design software vendor: Canva"),
    "NOTION": ("Software", 0.95, "Matched productivity SaaS vendor: Notion"),
    "SLACK": ("Software", 0.95, "Matched team communication SaaS vendor: Slack"),
    "ZOOM.US": ("Software", 0.95, "Matched video conferencing vendor: Zoom"),
    "HEROKU": ("Software", 0.95, "Matched hosting/cloud platform: Heroku"),
    "AWS": ("Software", 0.95, "Matched cloud infrastructure vendor: AWS"),
    "DIGITALOCEAN": ("Software", 0.95, "Matched cloud hosting vendor: DigitalOcean"),
    
    # Travel & Transport
    "UBER": ("Travel & Transport", 0.95, "Matched rideshare transportation provider: Uber"),
    "LYFT": ("Travel & Transport", 0.95, "Matched rideshare transportation provider: Lyft"),
    "CAREEM": ("Travel & Transport", 0.95, "Matched rideshare transportation provider: Careem"),
    "AMTRAK": ("Travel & Transport", 0.95, "Matched rail transit provider: Amtrak"),
    "DELTA AIR": ("Travel & Transport", 0.95, "Matched airline carrier: Delta Air Lines"),
    "UNITED AIRLINES": ("Travel & Transport", 0.95, "Matched airline carrier: United Airlines"),
    "AMERICAN AIR": ("Travel & Transport", 0.95, "Matched airline carrier: American Airlines"),
    
    # Meals & Coffee (Flagged as 50% deductible under IRS Schedule C rules)
    "BLUE BOTTLE": ("Meals & Coffee", 0.92, "Matched coffee/beverage vendor (subject to 50% business meal deduction rules)"),
    "STARBUCKS": ("Meals & Coffee", 0.92, "Matched coffee shop vendor (subject to 50% business meal deduction rules)"),
    "PEETS COFFEE": ("Meals & Coffee", 0.92, "Matched coffee vendor (subject to 50% business meal deduction rules)"),
    "DUNKIN": ("Meals & Coffee", 0.92, "Matched food & beverage vendor (subject to 50% business meal deduction rules)"),
    
    # Office Supplies & Equipment
    "OFFICE DEPOT": ("Office Supplies & Equipment", 0.95, "Matched office equipment and stationery supplier: Office Depot"),
    "STAPLES": ("Office Supplies & Equipment", 0.95, "Matched office supplies vendor: Staples"),
    "BEST BUY": ("Office Supplies & Equipment", 0.92, "Matched electronics & hardware vendor: Best Buy"),
    "MICRO CENTER": ("Office Supplies & Equipment", 0.92, "Matched computer hardware vendor: Micro Center"),
    
    # Internet & Utilities
    "COMCAST": ("Internet & Utilities", 0.95, "Matched telecommunications/internet provider: Comcast"),
    "VERIZON": ("Internet & Utilities", 0.95, "Matched mobile/internet carrier: Verizon"),
    "AT&T": ("Internet & Utilities", 0.95, "Matched telecommunications carrier: AT&T"),
    "T-MOBILE": ("Internet & Utilities", 0.95, "Matched mobile carrier: T-Mobile"),
    "SPECTRUM": ("Internet & Utilities", 0.95, "Matched broadband ISP: Spectrum"),
    
    # Advertising & Marketing
    "GOOGLE ADS": ("Advertising & Marketing", 0.98, "Matched digital advertising network: Google Ads"),
    "META ADS": ("Advertising & Marketing", 0.98, "Matched digital marketing network: Meta/Facebook Ads"),
    "FACEBOOK ADS": ("Advertising & Marketing", 0.98, "Matched digital marketing network: Meta/Facebook Ads"),
    "LINKEDIN ADS": ("Advertising & Marketing", 0.98, "Matched professional advertising service: LinkedIn Ads"),
    
    # Professional Services
    "H&R BLOCK": ("Professional Services", 0.95, "Matched professional accounting & tax preparation: H&R Block"),
    "SMITH & ASSOC": ("Professional Services", 0.95, "Matched legal/advisory firm: Smith & Assoc"),
    "LEGALZOOM": ("Professional Services", 0.95, "Matched legal compliance provider: LegalZoom"),
}

# Regex / keyword patterns
TRANSFER_PATTERNS = [
    r"\bTRANSFER\b.*(SAVINGS|CHECKING|ACC|ACCOUNT)",
    r"\bONLINE (XFER|TRANSFER)\b",
    r"\bTRANSFER BETWEEN\b",
    r"\bAUTOPAY\b.*(CREDIT CARD|BILL PAYMENT|CARD PAYMENT)",
    r"\bPAYMENT - THANK YOU\b",
    r"\bCREDIT CARD PAYMENT\b",
    r"\bINTERNAL TRANSFER\b",
]

REFUND_PATTERNS = [
    r"\bREFUND\b",
    r"\bRETURN\b",
    r"\bREVERSAL\b",
    r"\bCHARGEBACK\b",
    r"\bCREDIT ADJ\b",
    r"\bRETURN/REFUND\b",
]

PERSONAL_PATTERNS = [
    r"\bPERSONAL\b",
    r"\bOWNER DRAW\b",
    r"\bGROCERY OUTLET\b",
    r"\bNETFLIX\b",
    r"\bSPOTIFY PERSONAL\b",
    r"\bATM CASH WITHDRAWAL\b",
]

INCOME_PATTERNS = [
    r"\bCLIENT PAYMENT\b",
    r"\bINVOICE\s*(#|\bPAID\b)",
    r"\bRETAINER\b",
    r"\bFREELANCE\s*(PAYMENT|RETAINER|DESIGN)\b",
    r"\bPAYMENT RECEIVED\b",
    r"\bDIRECT DEPOSIT\b.*CLIENT",
]

BANK_FEE_PATTERNS = [
    r"\b(MONTHLY|ACCOUNT|SERVICE)\s*(FEE|CHARGE)\b",
    r"\bOVERDRAFT FEE\b",
    r"\bWIRE TRANSFER (INCOMING|OUTGOING)?\s*FEE\b",
    r"\bATM (SURCHARGE|FEE)\b",
    r"\bFOREIGN TRANSACTION FEE\b",
    r"\bBANK FEE\b",
]

# Patterns explicitly flagged as ambiguous or requiring manual verification
AMBIGUOUS_PATTERNS = [
    (r"\bJOES CAFE\b|\bCAFE \d{3,}\b", "Ambiguous merchant with numeric descriptor ('Joe's Cafe 9921'); requires verification whether business meal, personal, or travel expense"),
    (r"\bAMAZON(\.COM)?(\*|\s)?", "Amazon transactions vary widely (office supplies, software, books, or personal items); requires manual line-item verification"),
    (r"\bSQUARE\s*\*\s*PAYMENT\b|\bSQ\s*\*\s*\d+", "Mangled generic payment processor descriptor without discernible merchant identity"),
    (r"\bPAYPAL\s*\*\s*MISC\b|\bPP\*\s*\d+", "Generic PayPal transfer without vendor detail"),
]


def normalize_description(text: str) -> str:
    """Strip repeated whitespaces, uppercase, and simplify noise chars."""
    if not text:
        return ""
    cleaned = text.upper().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def categorize_transaction(description: str, amount: Decimal) -> tuple[str, float, str, bool, str]:
    """
    Categorizes a transaction using layered deterministic rules.
    Returns:
        (category, confidence, reason, needs_review, direction)
    """
    norm = normalize_description(description)
    if not norm:
        return ("Needs Review", 0.0, "Empty or missing transaction description", True, "other")

    # Determine default direction based on sign
    # Negative = expense / outflow; Positive = inflow
    is_positive = amount > Decimal(0)
    direction = "income" if is_positive else "expense"

    # LAYER 1: Explicit Internal Transfers & Account Settlements
    for pattern in TRANSFER_PATTERNS:
        if re.search(pattern, norm, re.IGNORECASE):
            return (
                "Transfer (not spending)",
                0.98,
                "Identified internal account transfer or card bill settlement (excluded from spending/income)",
                False,
                "transfer",
            )

    # LAYER 2: Explicit Refunds, Returns, and Chargebacks
    for pattern in REFUND_PATTERNS:
        if re.search(pattern, norm, re.IGNORECASE):
            # A refund is positive cash flow or offset, but NOT business income
            return (
                "Refund",
                0.95,
                "Identified refund or return credit (offsets expenses; never counted as operating income)",
                False,
                "refund",
            )

    # LAYER 3: Owner Draw / Personal Purchases on Business Account
    for pattern in PERSONAL_PATTERNS:
        if re.search(pattern, norm, re.IGNORECASE):
            return (
                "Personal / Owner Draw",
                0.92,
                "Identified personal expense or owner draw (non-deductible personal classification)",
                False,
                "expense" if not is_positive else "income",
            )

    # LAYER 4: Ambiguous Merchants & Processors (Conservative Routing)
    for pattern, note in AMBIGUOUS_PATTERNS:
        if re.search(pattern, norm, re.IGNORECASE):
            return (
                "Needs Review",
                0.35,
                note,
                True,
                direction,
            )

    # LAYER 5: Inbound Client Revenue / Invoices
    for pattern in INCOME_PATTERNS:
        if re.search(pattern, norm, re.IGNORECASE):
            if is_positive:
                return (
                    "Income",
                    0.96,
                    "Identified verified freelance client payment or invoice revenue",
                    False,
                    "income",
                )
            else:
                # If negative with invoice label, could be client rebate or refund
                return (
                    "Needs Review",
                    0.45,
                    "Inflow keyword detected on negative transaction; review for rebate or client adjustment",
                    True,
                    direction,
                )

    # LAYER 6: Bank & Account Fees
    for pattern in BANK_FEE_PATTERNS:
        if re.search(pattern, norm, re.IGNORECASE):
            return (
                "Bank Fees",
                0.92,
                "Matched financial institution service or processing fee",
                False,
                "expense",
            )

    # LAYER 7: Exact Merchant Lookup
    for merchant_key, (cat, conf, res) in MERCHANT_EXACT_RULES.items():
        # Match as word boundary or exact prefix/mangled token
        pattern = rf"(^|\b|[\*\#]){re.escape(merchant_key)}($|\b|[\*\#\s\d])"
        if re.search(pattern, norm, re.IGNORECASE):
            return (cat, conf, res, False, "expense")

    # LAYER 8: Mangled Processor Patterns (Square, Toast, Stripe)
    # E.g. SQ *ARTISAN BAKERY, TST* DOWNTOWN BISTRO
    if norm.startswith(("SQ *", "SQUARE *", "TST*")):
        sub_desc = re.sub(r"^(SQ\s*\*|SQUARE\s*\*|TST\s*\*)\s*", "", norm)
        # Check sub-descriptor for coffee / bakery / food
        if any(w in sub_desc for w in ["BAKERY", "CAFE", "COFFEE", "BISTRO", "RESTAURANT", "GRILL", "PIZZA"]):
            return (
                "Meals & Coffee",
                0.86,
                f"Matched processor merchant with food/beverage keyword: '{sub_desc}' (50% business deduction rule)",
                False,
                "expense",
            )

    # LAYER 9: Broad Keyword Heuristics (with conservative confidence thresholds)
    # Travel
    if any(k in norm for k in ["AIRFARE", "AIRLINE", "FLIGHT", "HOTEL", "TAXI", "CAR RENTAL", "COMMUTE"]):
        return (
            "Travel & Transport",
            0.82,
            "Matched transit/travel keyword heuristic",
            False,
            "expense",
        )

    # Meals
    if any(k in norm for k in ["COFFEE", "BAKERY", "BISTRO", "RESTAURANT", "DINER"]):
        return (
            "Meals & Coffee",
            0.80,
            "Matched meal/beverage keyword heuristic (50% business deduction rule)",
            False,
            "expense",
        )

    # Utilities
    if any(k in norm for k in ["BROADBAND", "INTERNET", "MOBILE BILL", "ELECTRICITY"]):
        return (
            "Internet & Utilities",
            0.82,
            "Matched utility service keyword heuristic",
            False,
            "expense",
        )

    # Office Supplies
    if any(k in norm for k in ["STATIONERY", "PRINTER", "KEYBOARD", "MONITOR", "DESK CHAIR", "OFFICE SUPPLIES"]):
        return (
            "Office Supplies & Equipment",
            0.82,
            "Matched office equipment/stationery keyword heuristic",
            False,
            "expense",
        )

    # Advertising
    if any(k in norm for k in ["ADWORDS", "PROMOTION", "MARKETING CAMPAIGN"]):
        return (
            "Advertising & Marketing",
            0.82,
            "Matched advertising/marketing keyword heuristic",
            False,
            "expense",
        )

    # Professional Services
    if any(k in norm for k in ["ACCOUNTANT", "LEGAL SERVICE", "TAX PREP", "CONSULTING FEE"]):
        return (
            "Professional Services",
            0.84,
            "Matched professional services advisory keyword heuristic",
            False,
            "expense",
        )

    # LAYER 10: Unmatched Inflows
    if is_positive:
        # A positive transaction that didn't match income, refund, or transfer
        # MUST NOT be blindly called Income!
        return (
            "Needs Review",
            0.30,
            "Unidentified incoming deposit; verify whether client payment, transfer, or capital investment",
            True,
            "income",
        )

    # LAYER 11: Ultimate Safe Fallback
    return (
        "Needs Review",
        0.20,
        "No deterministic rule matched with high confidence — manual categorization required",
        True,
        "expense",
    )
