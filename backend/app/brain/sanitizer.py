"""
Merchant description cleaning and normalization engine.
"""

import re

# POS / aggregator prefixes to strip
POS_PREFIX_PATTERNS = [
    r"^CHECKCARD\s+\d{4}\s+",
    r"^CHECKCARD\s+",
    r"^POS\s+PURCHASE\s+",
    r"^DEBIT\s+CARD\s+PURCHASE\s+",
    r"^CARD\s+PURCHASE\s+",
    r"^RECURRING\s+TRANSACTION\s+",
    r"^PURCHASE\s+AUTHORIZED\s+ON\s+\d{2}/\d{2}\s+",
    r"^PURCHASE\s+AUTHORIZED\s+ON\s+",
    r"^WITHDRAWAL\s+DEBIT\s+",
    r"^PURCHASE\s+",
    r"^DIRECT\s+DEBIT\s+",
    r"^ONLINE\s+PAYMENT\s+",
    r"^SQ\s*\*\s*",
    r"^TST\s*\*\s*",
    r"^PAYPAL\s*\*\s*",
    r"^PY\s*\*\s*",
]

# Patterns to remove noise: phone numbers, store numbers, URLs, dates, IDs
NOISE_PATTERNS = [
    # Bank transaction / reference prefixes
    r"\b(?:DES|ID|CO|REF|AUTH|PPD\s+ID|CCD\s+ID|INDN|TRACE):\s*[\w\d]+",
    # Phone numbers
    r"\b1?[-.]?8\d{2}[-.]\d{3}[-.]\d{4}\b",
    r"\b\d{3}[-.]\d{3}[-.]\d{4}\b",
    r"\b8\d{9}\b",
    # Store / transaction numbers: #1234, STORE 1234, NO. 12
    r"#\s*\d+\b",
    r"\bSTORE\s*(?:#\s*)?\d+\b",
    r"\bNO\.?\s*\d+\b",
    # Long numeric IDs or ticket numbers (e.g. Delta 0062839201842)
    r"\b\d{8,18}\b",
    # Trailing transaction ID codes like 2X91K3, 9XK8 (alphanumeric 4-12 chars with digits)
    r"\b(?=[A-Z0-9]*[0-9])(?=[A-Z0-9]*[A-Z])[A-Z0-9]{4,12}\b",
    # Dates: MM/DD/YYYY or MM/DD or MM-DD
    r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",
    # URLs and web domains
    r"https?://\S+",
    r"www\.\S+",
    r"\.(?:COM|IO|NET|ORG|CO|DEV|AI|APP|US|BIZ|TECH)\b",
    # Marketplace noise suffix
    r"\bMKTP\b",
    # Common trip/ride indicators
    r"\*TRIP\b",
    r"\*ORDER\b",
]

# Known US states / country codes at word boundaries
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "USA", "US"
]

# Common major city names in statement metadata
MAJOR_CITIES = [
    "SAN FRANCISCO", "NEW YORK", "LOS ANGELES", "SEATTLE", "AUSTIN",
    "CHICAGO", "BOSTON", "SAN JOSE", "MOUNTAIN VIEW", "REDMOND",
    "MENLO PARK", "PALO ALTO", "SAN DIEGO", "DALLAS", "ATLANTA",
    "DENVER", "PORTLAND", "MIAMI", "BROOKLYN", "MANHATTAN"
]

# Abbreviation expansions
ABBREVIATIONS = {
    r"\bAMZN\b": "AMAZON",
    r"\bAMAZON\s+MKTP\b": "AMAZON",
    r"\bAPL\b": "APPLE",
    r"\bMSFT\b": "MICROSOFT",
    r"\bGOOG\b": "GOOGLE",
    r"\bGITHUB INC\b": "GITHUB",
    r"\bAWS\s+SERVICES?\b": "AWS",
    r"\bAMAZON WEB SERVICES\b": "AWS",
    r"\bVERCEL INC\b": "VERCEL",
    r"\bSTRIPE INC\b": "STRIPE",
    r"\bSTARBUCKS STORE\b": "STARBUCKS",
}


def sanitize_merchant(raw_text: str) -> str:
    """
    Sanitize and clean a raw bank description into a clean, canonical merchant name.
    
    Steps:
    1. Validate non-empty text (return "UNKNOWN" for empty/whitespace).
    2. Repeatedly strip known POS/aggregator prefixes (SQ *, TST*, CHECKCARD).
    3. Expand standard abbreviations early (AMZN -> AMAZON, APL -> APPLE).
    4. Strip noise patterns (store numbers, ticket numbers, transaction IDs, URLs).
    5. Strip major city and state location suffixes.
    6. Normalize whitespace and boundary punctuation.
    7. Fall back to raw uppercased if result is empty.
    """
    if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
        return "UNKNOWN"

    cleaned = raw_text.strip().upper()
    original_raw = cleaned

    # 1. Strip POS prefixes repeatedly
    changed = True
    while changed:
        prev = cleaned
        for pattern in POS_PREFIX_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        changed = (cleaned != prev)

    # 2. Expand abbreviations early if part of prefix clean
    for pattern, replacement in ABBREVIATIONS.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # 3. Remove noise patterns
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    # 4. Remove location suffixes (cities and states)
    for city in MAJOR_CITIES:
        cleaned = re.sub(rf"\b{re.escape(city)}\b", " ", cleaned, flags=re.IGNORECASE)

    for state in US_STATES:
        cleaned = re.sub(rf"\b{state}\b(?:\s+USA|\s+US)?$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(rf"\b{state}\b", " ", cleaned, flags=re.IGNORECASE)

    # 5. Clean up non-alphanumeric noise at boundaries
    cleaned = re.sub(r"[^\w\s&'-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Second pass for abbreviation expansion on cleaned tokens
    for pattern, replacement in ABBREVIATIONS.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # 6. Fallback if empty or single character
    if len(cleaned) < 2:
        fallback = re.sub(r"^(?:CHECKCARD|POS PURCHASE|SQ \*|TST\*)\s*", "", original_raw).strip()
        if len(fallback) >= 2:
            return fallback
        return original_raw if original_raw.strip() else "UNKNOWN"

    return cleaned
