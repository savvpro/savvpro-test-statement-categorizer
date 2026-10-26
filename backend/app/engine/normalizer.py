import re
from typing import Tuple


class MerchantNormalizer:
    """
    Sanitizes raw, messy bank statement descriptions into clean canonical merchant names.
    Removes POS merchant codes, payment gateway prefixes, phone numbers, store numbers,
    trailing dates, state codes, and transaction noise.
    """

    # Payment processors and POS prefix junk
    PREFIX_PATTERNS = [
        r"^SQ\s*\*\s*",                     # Square: SQ *JOES CAFE
        r"^TST\s*\*\s*",                    # Toast POS: TST* BLUE BOTTLE
        r"^PAYPAL\s*\*\s*",                 # PayPal: PAYPAL *GITHUB INC
        r"^AMZN\s+Mktp\s+(?:US\s*)?\*\s*",  # Amazon Marketplace: AMZN Mktp US*
        r"^AMZN\s+MKTP\s*\*\s*",            # AMZN MKTP *
        r"^AMAZON\.COM\s*\*\s*",            # AMAZON.COM *
        r"^APPLE\.COM\/BILL\s*",            # Apple: APPLE.COM/BILL
        r"^GOOGLE\s*\*\s*",                 # Google: GOOGLE *WORKSPACE
        r"^SP\s*\*\s*",                     # Shopify: SP *FIGMA
        r"^STRIPE\s*\*\s*",                 # Stripe payments: STRIPE *HOSTING
        r"^CHECKCARD\s+\d+\s*",             # Debit card slip: CHECKCARD 1024
        r"^POS\s+(?:PURCHASE|DEBIT)\s*",    # POS PURCHASE
        r"^DEBIT\s+CARD\s+PURCHASE\s*",     # DEBIT CARD PURCHASE
        r"^PURCHASE\s+AUTHORIZED\s+ON\s+\d{2}\/\d{2}\s*",  # Chase authorization note
        r"^WITHDRAWAL\s+DEBIT\s*",
        r"^ACH\s+(?:DEBIT|CREDIT)\s*",
        r"^RECURRING\s+PAYMENT\s*",
    ]

    # Specific common merchant cleanup aliases
    KNOWN_ALIASES = {
        "ADOBE": "Adobe Creative Cloud",
        "ADOBE SYSTEMS": "Adobe Creative Cloud",
        "FIGMA": "Figma",
        "FIGMA INC": "Figma",
        "GITHUB": "GitHub",
        "AWS": "Amazon Web Services (AWS)",
        "AMAZON WEB SERVICES": "Amazon Web Services (AWS)",
        "OPENAI": "OpenAI (ChatGPT)",
        "CANVA": "Canva",
        "NOTION": "Notion Labs",
        "SLACK": "Slack Technologies",
        "ZOOM": "Zoom Video Communications",
        "VERCEL": "Vercel",
        "UBER": "Uber",
        "UBER TRIP": "Uber",
        "LYFT": "Lyft",
        "DELTA AIR": "Delta Air Lines",
        "DELTA AIR LINES": "Delta Air Lines",
        "UNITED AIRLINES": "United Airlines",
        "STARBUCKS": "Starbucks Coffee",
        "BLUE BOTTLE": "Blue Bottle Coffee",
        "UPWORK": "Upwork Escrow",
        "STRIPE": "Stripe Payout/Fee",
        "APPLE": "Apple Store",
        "APPLE STORE": "Apple Store",
        "BEST BUY": "Best Buy",
        "COMCAST": "Comcast Internet",
        "AMAZON": "Amazon",
        "AMZN": "Amazon",
    }

    @classmethod
    def clean(cls, raw: str) -> Tuple[str, str]:
        """
        Takes raw bank statement text and returns:
        (clean_merchant_display, normalized_key)
        """
        if not raw:
            return ("Unknown Merchant", "unknown")

        text = raw.strip()

        # Step 1: Strip payment processor prefixes (case-insensitive)
        for pattern in cls.PREFIX_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

        # Step 2: Handle Amazon marketplace patterns specifically
        if re.search(r"\b(?:amzn|amazon)\b", text, flags=re.IGNORECASE):
            text = "Amazon"

        # Step 3: Strip phone numbers
        text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", " ", text)
        text = re.sub(r"\b800\d{7}\b", " ", text)

        # Step 4: Strip URLs
        text = re.sub(r"\b(?:https?:\/\/)?(?:www\.)?[a-z0-9-]+\.(?:com|org|io|net|us|ai|co)(?:\/[^\s]*)?\b", " ", text, flags=re.IGNORECASE)

        # Step 5: Strip trailing store numbers / alphanumeric ids
        text = re.sub(r"#\s*[A-Z0-9-]+\b", " ", text)
        text = re.sub(r"\bSTORE\s*#?\s*\d+\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bLOC\s*#?\s*\d+\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bTERMINAL\s*\d+\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bREF\s*#?\s*[A-Z0-9]+\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bACC\s*#?\s*\d+\b", " ", text, flags=re.IGNORECASE)
        # Strip stand-alone 4-5 digit store/postal numbers
        text = re.sub(r"\b\d{4,5}\b", " ", text)

        # Step 6: Strip US state and country codes at ends or boundaries
        text = re.sub(r"\b(?:CA|NY|TX|WA|FL|IL|GA|CO|NC|MA|PA|VA|OR)\b(?:\s+(?:US|USA))?", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(?:US|USA)\b", " ", text, flags=re.IGNORECASE)

        # Step 7: Strip common city names if at the end
        text = re.sub(r"\b(?:SAN FRANCISCO|SEATTLE|SAN JOSE|MOUNTAIN VIEW|AUSTIN|ATLANTA|NEW YORK)\b", " ", text, flags=re.IGNORECASE)

        # Step 8: Remove non-alphanumeric punctuation except apostrophe
        text = re.sub(r"^[^\w]+|[^\w\s']+$", "", text)
        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            text = raw.strip()

        upper_text = text.upper()

        # Check known aliases
        for alias_key, canonical_name in cls.KNOWN_ALIASES.items():
            if upper_text == alias_key or upper_text.startswith(alias_key + " ") or f" {alias_key} " in f" {upper_text} ":
                return (canonical_name, canonical_name.lower())

        # Proper casing
        clean_name = " ".join(word.capitalize() for word in text.split())
        return (clean_name, clean_name.lower())
