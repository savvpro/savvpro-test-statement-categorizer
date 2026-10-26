import re

# Common bank transaction prefixes to strip
PREFIX_PATTERNS = [
    r"^POS\s+(?:PURCHASE|DEBIT|TRANSACTION)?\b",
    r"^CHECKCARD\s+\d*\b",
    r"^DEBIT\s+CARD\s+(?:PURCHASE|TRANSACTION)?\b",
    r"^PURCHASE\s+AUTHORIZED\s+ON\s+\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",
    r"^RECURRING\s+PAYMENT\s+AUTHORIZED\s+ON\s+\d{1,2}[/-]\d{1,2}\b",
    r"^AUTOMATIC\s+PAYMENT\s+-\s+THANK\s+YOU\b",
    r"^PAYMENT\s+THANK\s+YOU\s+-\s+WEB\b",
    r"^DIRECT\s+DEP\s+(?:-\s+)?",
    r"^ACH\s+(?:TRANSACTION|DEBIT|CREDIT)?\s*(?:-\s*)?",
    r"^ONLINE\s+BANKING\s+TRANSFER\s*(?:-\s*)?",
]

# Merchant payment processor wrappers like "SQ *", "TST*", "PAYPAL *", "SP *", "STRIPE *"
AGGREGATOR_PATTERNS = [
    r"\b(?:PAYPAL|PP)\s*\*+\s*",
    r"\bSQ\s*\*+\s*",
    r"\bTST\s*\*+\s*",
    r"\bSP\s*\*+\s*",
    r"\bSTRIPE\s*\*+\s*",
    r"\bFIVERR\s*\*+\s*",
    r"\bUPWORK\s*\*+\s*",
]

# US State abbreviations
US_STATES = (
    r"AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|"
    r"MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|"
    r"DC|PR|US|USA"
)


def normalize_description(raw: str) -> str:
    """
    Cleans and standardizes raw bank transaction descriptions:
    - Converts to uppercase
    - Strips common bank prefixes (POS PURCHASE, CHECKCARD, etc.)
    - Removes payment gateway wrappers (PAYPAL *, SQ *, TST*)
    - Strips store numbers, reference codes, phone numbers, auth codes
    - Removes embedded dates and trailing city/state/postal codes
    - Replaces symbols (*, -, _) with single space and trims whitespace
    """
    if not raw or not isinstance(raw, str):
        return ""

    text = raw.upper().strip()

    # Step 1: Strip common banking transaction prefixes
    for pattern in PREFIX_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Step 2: Strip payment aggregator markers
    for pattern in AGGREGATOR_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Step 3: Specific entity cleanups
    # URLs with path (amzn.com/bill -> amzn.com)
    text = re.sub(r"\b([A-Z0-9.-]+\.[A-Z]{2,4})/[A-Z0-9_/.-]*", r"\1", text, flags=re.IGNORECASE)

    # Phone numbers
    text = re.sub(r"\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", " ", text)

    # Reference / Auth / Terminal / Card codes (before stripping '#' standalone)
    text = re.sub(
        r"\b(?:AUTH|APPR|REF|SEQ|TERM|TERMINAL|ID|TRACE|TXN|BATCH|MCC)[\s#:]*[A-Z0-9]+\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bCARD\s*\d{4}\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bACCT\s*(?:ENDING\s+IN\s+)?\d{3,4}\b", " ", text, flags=re.IGNORECASE)

    # Store numbers (#123, STORE 9482)
    text = re.sub(r"#\s*\d+", " ", text)
    text = re.sub(r"\bSTORE\s*(?:NO\.?|#)?\s*\d+\b", " ", text, flags=re.IGNORECASE)

    # Standalone leftover ref tokens
    text = re.sub(r"\b(?:AUTH|APPR|REF|SEQ|TERM|TERMINAL|TRACE|TXN|BATCH)\b", " ", text, flags=re.IGNORECASE)

    # Embedded dates (10/24, 10/15/2024, 2024-08-01)
    text = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " ", text)
    text = re.sub(r"\b\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?\b", " ", text)

    # Postal codes (94107, 98101-1234)
    text = re.sub(r"\b\d{5}(?:-\d{4})?\b", " ", text)

    # Trailing city + state: requires whitespace preceding the city name to avoid consuming single-word merchants
    text = re.sub(
        rf"(?<=\s)[A-Z]{{2,15}}(?:\s+[A-Z]{{2,15}})?\s+(?:{US_STATES})(?:\s+(?:US|USA))?\s*$",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Punctuation / separators: replace *, -, _, /, #, :, ; with spaces
    text = re.sub(r"[*_\-/:;#\\]+", " ", text)

    # Collapse multiple spaces and strip
    text = re.sub(r"\s+", " ", text).strip()

    return text
