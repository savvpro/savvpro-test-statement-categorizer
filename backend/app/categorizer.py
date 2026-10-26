"""
categorizer.py

This is the "brain" of the app. Took me a while to figure out the right approach
here - started with just keyword matching but it was too noisy, so I added a
merchant lookup table first and fall back to patterns/keywords only when needed.

No AI at runtime - the task specifically said not to use GPT/Claude/Gemini for
the actual categorization decisions, so everything here is deterministic rule-based logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# Categories I picked for a freelance designer use case.
# Could be extended for other use cases pretty easily.
class Category(str, Enum):
    SOFTWARE = "Software & Subscriptions"
    TRAVEL = "Travel & Transport"
    FOOD_DINING = "Food & Dining"
    OFFICE_SUPPLIES = "Office & Supplies"
    MARKETING = "Marketing & Advertising"
    EDUCATION = "Education & Training"
    PROFESSIONAL_SERVICES = "Professional Services"
    HEALTH_WELLNESS = "Health & Wellness"
    TRANSFER = "Transfer / Non-Expense"
    NEEDS_REVIEW = "Needs Review"


@dataclass
class CategorizationResult:
    category: Category
    confidence: float   # 0.0 to 1.0
    reason: str         # shown in the UI so the user understands why
    is_review: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_review = self.category == Category.NEEDS_REVIEW


# ---------------------------------------------------------------------------
# Merchant lookup - I built this list manually based on common freelancer expenses.
# It's not exhaustive but covers 80%+ of real transactions I've seen.
# TODO: could load this from a JSON file to make it easier to extend
# ---------------------------------------------------------------------------
MERCHANT_MAP: dict[str, tuple[Category, str]] = {
    # Software & Subscriptions
    "adobe": (Category.SOFTWARE, "Adobe Creative Cloud / products"),
    "adobe creative cloud": (Category.SOFTWARE, "Adobe Creative Cloud"),
    "figma": (Category.SOFTWARE, "Figma design tool"),
    "notion": (Category.SOFTWARE, "Notion productivity app"),
    "slack": (Category.SOFTWARE, "Slack team messaging"),
    "github": (Category.SOFTWARE, "GitHub code hosting"),
    "dropbox": (Category.SOFTWARE, "Dropbox cloud storage"),
    "google workspace": (Category.SOFTWARE, "Google Workspace"),
    "gsuite": (Category.SOFTWARE, "Google Workspace (G Suite)"),
    "microsoft 365": (Category.SOFTWARE, "Microsoft 365"),
    "microsoft office": (Category.SOFTWARE, "Microsoft Office"),
    "zoom": (Category.SOFTWARE, "Zoom video conferencing"),
    "loom": (Category.SOFTWARE, "Loom screen recording"),
    "asana": (Category.SOFTWARE, "Asana project management"),
    "trello": (Category.SOFTWARE, "Trello project management"),
    "canva": (Category.SOFTWARE, "Canva design tool"),
    "sketch": (Category.SOFTWARE, "Sketch design tool"),
    "invision": (Category.SOFTWARE, "InVision prototyping"),
    "framer": (Category.SOFTWARE, "Framer design tool"),
    "webflow": (Category.SOFTWARE, "Webflow website builder"),
    "squarespace": (Category.SOFTWARE, "Squarespace website builder"),
    "wordpress": (Category.SOFTWARE, "WordPress"),
    "netlify": (Category.SOFTWARE, "Netlify hosting"),
    "vercel": (Category.SOFTWARE, "Vercel hosting"),
    "aws": (Category.SOFTWARE, "Amazon Web Services"),
    "digitalocean": (Category.SOFTWARE, "DigitalOcean cloud"),
    "heroku": (Category.SOFTWARE, "Heroku platform"),
    "spotify": (Category.SOFTWARE, "Spotify (background music for work)"),
    "1password": (Category.SOFTWARE, "1Password password manager"),
    "lastpass": (Category.SOFTWARE, "LastPass password manager"),
    "nvim": (Category.SOFTWARE, "Neovim / editor plugin"),
    "jetbrains": (Category.SOFTWARE, "JetBrains IDE"),
    "font awesome": (Category.SOFTWARE, "Font Awesome icons"),
    "envato": (Category.SOFTWARE, "Envato creative assets"),
    "shutterstock": (Category.SOFTWARE, "Shutterstock stock images"),
    "adobe stock": (Category.SOFTWARE, "Adobe Stock"),
    "istock": (Category.SOFTWARE, "iStock"),
    "unsplash": (Category.SOFTWARE, "Unsplash"),

    # Travel & Transport
    "uber": (Category.TRAVEL, "Uber ride"),
    "lyft": (Category.TRAVEL, "Lyft ride"),
    "delta": (Category.TRAVEL, "Delta Airlines"),
    "southwest": (Category.TRAVEL, "Southwest Airlines"),
    "american airlines": (Category.TRAVEL, "American Airlines"),
    "united airlines": (Category.TRAVEL, "United Airlines"),
    "jetblue": (Category.TRAVEL, "JetBlue Airways"),
    "expedia": (Category.TRAVEL, "Expedia travel booking"),
    "airbnb": (Category.TRAVEL, "Airbnb accommodation"),
    "booking.com": (Category.TRAVEL, "Booking.com accommodation"),
    "hotels.com": (Category.TRAVEL, "Hotels.com"),
    "hilton": (Category.TRAVEL, "Hilton hotel"),
    "marriott": (Category.TRAVEL, "Marriott hotel"),
    "hyatt": (Category.TRAVEL, "Hyatt hotel"),
    "enterprise": (Category.TRAVEL, "Enterprise car rental"),
    "hertz": (Category.TRAVEL, "Hertz car rental"),
    "avis": (Category.TRAVEL, "Avis car rental"),
    "amtrak": (Category.TRAVEL, "Amtrak train"),
    "mta": (Category.TRAVEL, "MTA transit"),
    "google maps": (Category.TRAVEL, "Google Maps / transit"),

    # Food & Dining
    "starbucks": (Category.FOOD_DINING, "Starbucks coffee"),
    "dunkin": (Category.FOOD_DINING, "Dunkin' Donuts"),
    "mcdonalds": (Category.FOOD_DINING, "McDonald's"),
    "chipotle": (Category.FOOD_DINING, "Chipotle"),
    "doordash": (Category.FOOD_DINING, "DoorDash food delivery"),
    "ubereats": (Category.FOOD_DINING, "Uber Eats food delivery"),
    "uber eats": (Category.FOOD_DINING, "Uber Eats food delivery"),
    "grubhub": (Category.FOOD_DINING, "Grubhub food delivery"),
    "postmates": (Category.FOOD_DINING, "Postmates food delivery"),
    "instacart": (Category.FOOD_DINING, "Instacart grocery delivery"),
    "whole foods": (Category.FOOD_DINING, "Whole Foods Market"),
    "trader joes": (Category.FOOD_DINING, "Trader Joe's"),
    "panera": (Category.FOOD_DINING, "Panera Bread"),
    "sweetgreen": (Category.FOOD_DINING, "Sweetgreen"),

    # Office & Supplies
    "amazon": (Category.OFFICE_SUPPLIES, "Amazon purchase"),
    "staples": (Category.OFFICE_SUPPLIES, "Staples office supplies"),
    "office depot": (Category.OFFICE_SUPPLIES, "Office Depot"),
    "best buy": (Category.OFFICE_SUPPLIES, "Best Buy electronics"),
    "apple store": (Category.OFFICE_SUPPLIES, "Apple Store hardware"),
    "apple.com": (Category.OFFICE_SUPPLIES, "Apple online purchase"),
    "b&h photo": (Category.OFFICE_SUPPLIES, "B&H Photo equipment"),
    "bhphotovideo": (Category.OFFICE_SUPPLIES, "B&H Photo/Video"),
    "wayfair": (Category.OFFICE_SUPPLIES, "Wayfair office furniture"),
    "ikea": (Category.OFFICE_SUPPLIES, "IKEA furniture/supplies"),
    "fedex": (Category.OFFICE_SUPPLIES, "FedEx shipping"),
    "ups store": (Category.OFFICE_SUPPLIES, "UPS Store"),
    "usps": (Category.OFFICE_SUPPLIES, "USPS postage"),

    # Marketing & Advertising
    "facebook ads": (Category.MARKETING, "Facebook Ads"),
    "meta ads": (Category.MARKETING, "Meta Ads"),
    "google ads": (Category.MARKETING, "Google Ads"),
    "twitter ads": (Category.MARKETING, "Twitter Ads"),
    "linkedin ads": (Category.MARKETING, "LinkedIn Ads"),
    "mailchimp": (Category.MARKETING, "Mailchimp email marketing"),
    "convertkit": (Category.MARKETING, "ConvertKit email marketing"),
    "klaviyo": (Category.MARKETING, "Klaviyo email marketing"),
    "hootsuite": (Category.MARKETING, "Hootsuite social media"),
    "buffer": (Category.MARKETING, "Buffer social media"),

    # Education & Training
    "udemy": (Category.EDUCATION, "Udemy course"),
    "coursera": (Category.EDUCATION, "Coursera course"),
    "skillshare": (Category.EDUCATION, "Skillshare course"),
    "masterclass": (Category.EDUCATION, "MasterClass"),
    "linkedin learning": (Category.EDUCATION, "LinkedIn Learning"),
    "pluralsight": (Category.EDUCATION, "Pluralsight"),
    "oreilly": (Category.EDUCATION, "O'Reilly Media"),
    "amazon books": (Category.EDUCATION, "Amazon book purchase"),
    "barnes noble": (Category.EDUCATION, "Barnes & Noble books"),

    # Transfers / Non-Expense
    "transfer to savings": (Category.TRANSFER, "Transfer to savings account"),
    "zelle": (Category.TRANSFER, "Zelle bank transfer"),
    "venmo": (Category.TRANSFER, "Venmo payment"),
    "paypal transfer": (Category.TRANSFER, "PayPal transfer"),
    "direct deposit": (Category.TRANSFER, "Direct deposit (income)"),
    "ach transfer": (Category.TRANSFER, "ACH bank transfer"),
    "wire transfer": (Category.TRANSFER, "Wire transfer"),
    "atm withdrawal": (Category.TRANSFER, "ATM cash withdrawal"),
    "bank of america": (Category.TRANSFER, "Bank transfer"),
    "chase bank": (Category.TRANSFER, "Chase bank transfer"),

    # Health & Wellness
    "planet fitness": (Category.HEALTH_WELLNESS, "Planet Fitness gym"),
    "equinox": (Category.HEALTH_WELLNESS, "Equinox gym"),
    "cvs pharmacy": (Category.HEALTH_WELLNESS, "CVS Pharmacy"),
    "walgreens": (Category.HEALTH_WELLNESS, "Walgreens Pharmacy"),
}

# ---------------------------------------------------------------------------
# Regex patterns - fallback when merchant lookup doesn't find anything.
# Order matters a lot here - learned this the hard way when UBER EATS was
# matching the UBER travel pattern before I moved it to the merchant map.
# More specific patterns should always come before generic ones.
# ---------------------------------------------------------------------------
PATTERN_RULES: list[tuple[re.Pattern, Category, str]] = [
    # Software / SaaS
    (re.compile(r"\bSUBSCRIPTION\b|\bSUBSCR\b|\bSUBS\b", re.I), Category.SOFTWARE, "Subscription keyword"),
    (re.compile(r"\bSAAS\b|\bSOFTWARE\b|\bLICENSE\b|\bLICENCE\b", re.I), Category.SOFTWARE, "Software/license keyword"),
    (re.compile(r"\bAPP STORE\b|\bGOOGLE PLAY\b|\bPLAY STORE\b", re.I), Category.SOFTWARE, "Mobile app store"),
    (re.compile(r"\bCLOUD\b|\bHOSTING\b|\bSERVER\b|\bDOMAIN\b|\bDNS\b", re.I), Category.SOFTWARE, "Cloud/hosting service"),

    # Travel
    (re.compile(r"\bUBER\s*\*", re.I), Category.TRAVEL, "Uber ride/service"),
    (re.compile(r"\bLYFT\s*\*", re.I), Category.TRAVEL, "Lyft ride"),
    (re.compile(r"\bAIRLINES?\b|\bAIRWAYS?\b|\bFLIGHT\b|\bBOARDING\b", re.I), Category.TRAVEL, "Airline / flight"),
    (re.compile(r"\bHOTEL\b|\bINN\b|\bSUITES?\b|\bLODGING\b|\bMOTEL\b", re.I), Category.TRAVEL, "Hotel / lodging"),
    (re.compile(r"\bCAR\s*RENTAL\b|\bRENT\s*A\s*CAR\b|\bRENTAL\b", re.I), Category.TRAVEL, "Car rental"),
    (re.compile(r"\bTRAIN\b|\bAMTRAK\b|\bMETRO\b|\bSUBWAY\b|\bBUS\s*TICKET\b", re.I), Category.TRAVEL, "Public transit"),
    (re.compile(r"\bPARKING\b|\bGARAGE\b", re.I), Category.TRAVEL, "Parking"),
    (re.compile(r"\bGAS\s*STATION\b|\bFUEL\b|\bSHELL\b|\bEXXON\b|\bCHEVRON\b|\bBP\s+\b", re.I), Category.TRAVEL, "Fuel / gas"),

    # Food & Dining
    (re.compile(r"\bRESTAURANT\b|\bEATERY\b|\bBISTRO\b|\bCAFE\b|\bCAFÉ\b|\bBAKERY\b|\bDINER\b|\bGRILL\b|\bBBQ\b", re.I), Category.FOOD_DINING, "Restaurant / cafe"),
    (re.compile(r"\bFOOD\s*DELIVERY\b|\bDELIVERY\s*FEE\b", re.I), Category.FOOD_DINING, "Food delivery"),
    (re.compile(r"\bCOFFEE\b|\bESPRESSO\b|\bLATTE\b|\bTEA\s*HOUSE\b", re.I), Category.FOOD_DINING, "Coffee shop"),
    (re.compile(r"\bGROCERY\b|\bSUPERMARKET\b|\bFOOD\s*MART\b|\bWHOLE\s*FOODS\b", re.I), Category.FOOD_DINING, "Grocery / supermarket"),
    (re.compile(r"\bPIZZA\b|\bSUSHI\b|\bBURGER\b|\bTACO\b|\bNOODLE\b|\bRAMEN\b", re.I), Category.FOOD_DINING, "Restaurant (cuisine type)"),

    # Office & Supplies
    (re.compile(r"\bAMZN\b|\bAMAZON\s*(MKTPL|MKTP|PRIME)?\b", re.I), Category.OFFICE_SUPPLIES, "Amazon purchase"),
    (re.compile(r"\bAPPLE\s*(STORE|\.COM|ICLOUD|MUSIC|TV\+?)?\b", re.I), Category.SOFTWARE, "Apple service/product"),
    (re.compile(r"\bOFFICE\s*(SUPPLY|SUPPLIES|DEPOT|MAX)\b", re.I), Category.OFFICE_SUPPLIES, "Office supplies store"),
    (re.compile(r"\bPRINT(ING)?\b|\bINK\b|\bTONER\b", re.I), Category.OFFICE_SUPPLIES, "Printing supplies"),
    (re.compile(r"\bEQUIPMENT\b|\bHARDWARE\b|\bCAMERA\b|\bSTUDIO\b", re.I), Category.OFFICE_SUPPLIES, "Equipment / hardware"),
    (re.compile(r"\bFEDEX\b|\bUPS\b|\bUSPS\b|\bSHIPPING\b|\bCOURIER\b", re.I), Category.OFFICE_SUPPLIES, "Shipping / courier"),

    # Marketing
    (re.compile(r"\bFACEBOOK\s*(ADS?|MARKETING)\b|\bMETA\s*ADS?\b", re.I), Category.MARKETING, "Facebook / Meta ads"),
    (re.compile(r"\bGOOGLE\s*ADS?\b|\bADWORDS\b", re.I), Category.MARKETING, "Google Ads"),
    (re.compile(r"\bADS?\s*(SPEND|CAMPAIGN|BOOST)\b|\bADVERTISING\b|\bPROMOTED\b", re.I), Category.MARKETING, "Advertising spend"),
    (re.compile(r"\bEMAIL\s*MARKETING\b|\bNEWSLETTER\b|\bCAMPAIGN\b", re.I), Category.MARKETING, "Email marketing"),

    # Education
    (re.compile(r"\bCOURSE\b|\bTRAINING\b|\bWORKSHOP\b|\bWEBINAR\b|\bCONFERENCE\b|\bSEMINAR\b", re.I), Category.EDUCATION, "Course / training event"),
    (re.compile(r"\bBOOK\b|\bEBOOK\b|\bE-BOOK\b|\bKINDLE\b|\bAUDIBLE\b", re.I), Category.EDUCATION, "Books / reading material"),
    (re.compile(r"\bTUTORIAL\b|\bMENTOR(SHIP)?\b|\bCOACHING\b", re.I), Category.EDUCATION, "Mentorship / coaching"),

    # Professional Services
    (re.compile(r"\bACCOUNT(ANT|ING)\b|\bCPA\b|\bBOOKKEEP\b|\bTAX\s*(PREP|SERVICE)\b", re.I), Category.PROFESSIONAL_SERVICES, "Accounting / tax service"),
    (re.compile(r"\bLAWYER\b|\bATTORNEY\b|\bLEGAL\b|\bNOTARY\b", re.I), Category.PROFESSIONAL_SERVICES, "Legal services"),
    (re.compile(r"\bFREELANC(ER|E)\b|\bCONTRACTOR\b|\bCONSULT(ANT|ING)\b", re.I), Category.PROFESSIONAL_SERVICES, "Freelancer / consultant"),
    (re.compile(r"\bFIVERR\b|\bUPWORK\b|\bTOPTAL\b|\b99DESIGNS\b", re.I), Category.PROFESSIONAL_SERVICES, "Freelance marketplace"),

    # Health & Wellness
    (re.compile(r"\bGYM\b|\bFITNESS\b|\bYOGA\b|\bPILATES\b|\bCROSSFIT\b", re.I), Category.HEALTH_WELLNESS, "Gym / fitness"),
    (re.compile(r"\bPHARMACY\b|\bRX\b|\bDRUGSTORE\b", re.I), Category.HEALTH_WELLNESS, "Pharmacy"),
    (re.compile(r"\bMEDICAL\b|\bDOCTOR\b|\bDR\.\s+\b|\bCLINIC\b|\bHOSPITAL\b", re.I), Category.HEALTH_WELLNESS, "Medical / healthcare"),

    # Transfers / Non-expense
    (re.compile(r"\bTRANSFER\b|\bWIRE\b|\bACH\b", re.I), Category.TRANSFER, "Bank transfer"),
    (re.compile(r"\bREFUND\b|\bCREDIT\s+BACK\b|\bCHARGEBACK\b|\bREVERSAL\b", re.I), Category.TRANSFER, "Refund / credit back"),
    (re.compile(r"\bATM\b|\bCASH\s*(BACK|WITHDRAWAL|ADVANCE)\b", re.I), Category.TRANSFER, "ATM / cash"),
    (re.compile(r"\bSALARY\b|\bPAYROLL\b|\bDIRECT\s*DEP(OSIT)?\b|\bDD\s+\b", re.I), Category.TRANSFER, "Payroll / income deposit"),
    (re.compile(r"\bINVOICE\s*(PAYMENT|PMT)\b|\bINV\s*#\d+\b", re.I), Category.TRANSFER, "Invoice payment received"),
]

# ---------------------------------------------------------------------------
# Keyword scoring - last resort when patterns don't match either.
# Each keyword has a weight (0-1). I tuned these manually by running the
# sample statement through and seeing what got misclassified.
# The "service" and "payment" keywords had to be lowered because they were
# causing everything to match Professional Services at first.
# ---------------------------------------------------------------------------
KEYWORD_WEIGHTS: dict[Category, list[tuple[str, float]]] = {
    Category.SOFTWARE: [
        ("software", 0.8), ("app", 0.5), ("digital", 0.4), ("online", 0.3),
        ("cloud", 0.6), ("saas", 0.9), ("api", 0.7), ("plugin", 0.7),
        ("platform", 0.4), ("tool", 0.4), ("service", 0.3), ("pro", 0.2),
    ],
    Category.TRAVEL: [
        ("travel", 0.9), ("trip", 0.8), ("flight", 0.9), ("hotel", 0.9),
        ("airline", 0.9), ("taxi", 0.8), ("ride", 0.6), ("transit", 0.8),
        ("transport", 0.8), ("rental", 0.6), ("parking", 0.7), ("gas", 0.5),
    ],
    Category.FOOD_DINING: [
        ("food", 0.8), ("cafe", 0.8), ("coffee", 0.8), ("restaurant", 0.9),
        ("diner", 0.8), ("eat", 0.6), ("grill", 0.7), ("pizza", 0.9),
        ("burger", 0.9), ("sushi", 0.9), ("bakery", 0.8), ("bar", 0.4),
    ],
    Category.OFFICE_SUPPLIES: [
        ("supply", 0.8), ("supplies", 0.8), ("office", 0.7), ("desk", 0.7),
        ("hardware", 0.7), ("equipment", 0.7), ("stationery", 0.9), ("print", 0.6),
        ("ink", 0.7), ("monitor", 0.8), ("keyboard", 0.8), ("cable", 0.6),
    ],
    Category.MARKETING: [
        ("ads", 0.9), ("advertising", 0.9), ("marketing", 0.9), ("campaign", 0.8),
        ("promotion", 0.7), ("boost", 0.6), ("sponsored", 0.8), ("influencer", 0.7),
    ],
    Category.EDUCATION: [
        ("course", 0.9), ("training", 0.8), ("learn", 0.7), ("book", 0.6),
        ("class", 0.7), ("school", 0.6), ("academy", 0.7), ("tutorial", 0.8),
        ("workshop", 0.8), ("conference", 0.7), ("seminar", 0.8),
    ],
    Category.PROFESSIONAL_SERVICES: [
        ("consulting", 0.9), ("consultant", 0.9), ("legal", 0.9), ("lawyer", 0.9),
        ("accounting", 0.9), ("accountant", 0.9), ("contractor", 0.8), ("freelance", 0.8),
        ("agency", 0.6), ("services", 0.4), ("professional", 0.5),
    ],
    Category.HEALTH_WELLNESS: [
        ("gym", 0.9), ("fitness", 0.9), ("health", 0.8), ("wellness", 0.9),
        ("pharmacy", 0.9), ("medical", 0.9), ("doctor", 0.9), ("clinic", 0.9),
        ("yoga", 0.9), ("spa", 0.7), ("dental", 0.9),
    ],
    Category.TRANSFER: [
        ("transfer", 0.9), ("wire", 0.8), ("ach", 0.9), ("refund", 0.9),
        ("credit", 0.5), ("payment", 0.4), ("deposit", 0.7), ("withdrawal", 0.8),
        ("atm", 0.9), ("cash", 0.6), ("payroll", 0.9),
    ],
}

# Anything below this gets flagged for manual review.
# 0.45 felt right after testing - higher (0.6) flagged too many legit ones,
# lower (0.3) let through too many bad guesses.
CONFIDENCE_THRESHOLD = 0.45


def _normalize(text: str) -> str:
    # strip punctuation and extra spaces, uppercase everything
    text = text.upper()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _merchant_lookup(description: str) -> Optional[tuple[Category, str]]:
    norm = description.lower().strip()
    # try progressively shorter prefixes first (handles trailing numbers/refs)
    for length in range(len(norm), 2, -1):
        key = norm[:length].strip()
        if key in MERCHANT_MAP:
            return MERCHANT_MAP[key]
    # then try contains check
    for merchant, result in MERCHANT_MAP.items():
        if merchant in norm:
            return result
    return None


def _pattern_match(description: str) -> Optional[tuple[Category, str]]:
    for pattern, category, reason in PATTERN_RULES:
        if pattern.search(description):
            return (category, reason)
    return None


def _keyword_score(description: str) -> tuple[Category, float]:
    """Score each category by keyword presence. Returns (best_category, confidence)."""
    words = set(_normalize(description).lower().split())
    scores: dict[Category, float] = {}

    for category, keyword_weights in KEYWORD_WEIGHTS.items():
        score = 0.0
        for keyword, weight in keyword_weights:
            if keyword in words or keyword in description.lower():
                score += weight
        scores[category] = score

    if not scores or max(scores.values()) == 0:
        return (Category.NEEDS_REVIEW, 0.0)

    best = max(scores, key=lambda c: scores[c])
    total = sum(scores.values())
    confidence = scores[best] / total if total > 0 else 0.0
    # multiply by 2 so a clear winner (50%+ of score mass) reaches ~1.0
    confidence = min(confidence * 2.0, 1.0)
    return (best, confidence)


def _is_refund(description: str, amount: Optional[float] = None) -> bool:
    """
    Refunds are money coming back - they shouldn't count as expenses.
    On credit card statements, positive amounts are usually credits/refunds.
    """
    refund_keywords = re.compile(
        r"\bREFUND\b|\bCREDIT\b|\bREVERSAL\b|\bCHARGEBACK\b|\bADJUSTMENT\b", re.I
    )
    if refund_keywords.search(description):
        return True
    if amount is not None and amount > 0:
        return True
    return False


def categorize(
    description: str,
    amount: Optional[float] = None,
    *,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> CategorizationResult:
    """
    Main entry point. Runs through the 3-stage pipeline and returns a result.
    If nothing is confident enough, returns NEEDS_REVIEW so the user can fix it.
    Better to say "not sure" than make a wrong guess for tax purposes.
    """
    if not description or not description.strip():
        return CategorizationResult(
            category=Category.NEEDS_REVIEW,
            confidence=0.0,
            reason="Empty description",
        )

    # check for refunds first - a refund is not an expense regardless of merchant
    if _is_refund(description, amount):
        return CategorizationResult(
            category=Category.TRANSFER,
            confidence=0.95,
            reason="Refund or credit — money back, not an expense",
        )

    # stage 1: merchant lookup (most reliable)
    match = _merchant_lookup(description)
    if match:
        category, reason = match
        return CategorizationResult(category=category, confidence=0.95, reason=reason)

    # stage 2: regex patterns
    match = _pattern_match(description)
    if match:
        category, reason = match
        return CategorizationResult(category=category, confidence=0.80, reason=f"Pattern: {reason}")

    # stage 3: keyword scoring (least reliable, may not clear the threshold)
    category, confidence = _keyword_score(description)

    if confidence < confidence_threshold:
        return CategorizationResult(
            category=Category.NEEDS_REVIEW,
            confidence=confidence,
            reason=f"Low confidence ({confidence:.0%}) — needs manual review",
        )

    return CategorizationResult(
        category=category,
        confidence=confidence,
        reason=f"Keyword match ({confidence:.0%})",
    )
