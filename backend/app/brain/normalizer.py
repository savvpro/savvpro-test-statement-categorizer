"""
Text Normalization & Noise Stripping Engine for Bank Statement Descriptions.
Extracts clean merchant names and tokens from messy transaction records.
"""

import re
from typing import Dict, Any, List

# Common noise patterns found in bank/credit card statements
PREFIX_PATTERNS = [
    r"^(?:POS\s+DEBIT|POS\s+PURCHASE|CHECKCARD|CHECK\s+CARD|DEBIT\s+CARD\s+PURCHASE)\s*[-:]?\s*",
    r"^(?:PURCHASE\s+AUTHORIZED\s+ON\s+\d{1,2}/\d{1,2})\s*",
    r"^(?:RECURRING\s+PAYMENT|AUTOMATIC\s+PAYMENT|SCHEDULED\s+PAYMENT|AUTOPAY)\s*[-:]?\s*",
    r"^(?:ACH\s+(?:DEBIT|CREDIT)|DIRECT\s+DEP(?:OSIT)?|WIRE\s+(?:IN|OUT))\s*[-:]?\s*",
    r"^(?:ONLINE\s+PMT|WEB\s+PAYMENT|BILL\s+PAYMENT)\s*[-:]?\s*",
    r"^(?:PAYPAL\s*\*\s*|SQ\s*\*\s*|TST\s*\*\s*|STRIPE\s*\*\s*|SP\s*\*\s*)",
    r"^(?:FEE:\s*|SERVICE\s+CHARGE:\s*)",
]

CARD_MASK_PATTERN = r"(?:X{2,}\d{3,4}|\*{2,}\d{3,4}|#\d{4,8}|CARD\s+\d{3,4})"
PHONE_PATTERN = r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
URL_PATTERN = r"(?:HTTPS?:\/\/)?(?:WWW\.)?([A-Z0-9.-]+\.(?:COM|IO|CO|NET|ORG|APP|DEV|AI|SO|US))"
STORE_NUM_PATTERN = r"(?:STORE|LOC|STR|SHOP|UNIT|BRANCH|TERMINAL|TERM)\s*#?\s*\d+"
DATE_PATTERN = r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b"

# US State abbreviations followed by optional zip code at the end of string
US_STATE_ZIP_PATTERN = r"\b(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\s+(?:\d{5}(?:-\d{4})?)?\b"
INTL_LOCATIONS = r"\b(?:IRL|GBR|CAN|AUS|DEU|FRA|NLD|SGP|CHE|JPN|UK|USA)\b"

REFUND_INDICATORS = [
    r"\bREFUND\b",
    r"\bREVERSAL\b",
    r"\bRETURN\b",
    r"\bCREDIT\s+VOUCHER\b",
    r"\bCHARGEBACK\b",
    r"\bDISPUTE\s+CREDIT\b",
]

TRANSFER_INDICATORS = [
    r"\bTRANSFER\s+TO\b",
    r"\bTRANSFER\s+FROM\b",
    r"\bXFER\b",
    r"\bOWNER(?:'S)?\s+DRAW\b",
    r"\bPAYMENT\s+THANK\s+YOU\b",
    r"\bAUTOPAY\s+PAYMENT\b",
    r"\bZELLE\s+TRANSFER\b",
    r"\bINTER-ACCOUNT\b",
    r"\bONLINE\s+BANKING\s+TRANSFER\b",
]

INCOME_INDICATORS = [
    r"\bCLIENT\s+(?:ACH\s+)?(?:PAYMENT|DEPOSIT|TRANSFER)\b",
    r"\bINVOICE\s*#?\d+\b",
    r"\bDIRECT\s+DEPOSIT\s+PAYROLL\b",
    r"\bSTRIPE\s+PAYOUT\b",
    r"\bPAYOUT\b",
    r"\bCONSULTING\s+REVENUE\b",
    r"\bWIRE\s+(?:IN|PAYMENT)\b",
]


class NormalizedDescription:
    def __init__(self, raw: str):
        self.raw = raw or ""
        self.cleaned = ""
        self.clean_merchant = ""
        self.tokens: List[str] = []
        self.is_refund_flag = False
        self.is_transfer_flag = False
        self.is_income_flag = False
        self.meta: Dict[str, Any] = {}
        self._normalize()

    def _normalize(self):
        text = self.raw.strip().upper()

        # Check directional/signal indicators before stripping
        for pat in REFUND_INDICATORS:
            if re.search(pat, text, re.IGNORECASE):
                self.is_refund_flag = True
                break

        for pat in TRANSFER_INDICATORS:
            if re.search(pat, text, re.IGNORECASE):
                self.is_transfer_flag = True
                break

        for pat in INCOME_INDICATORS:
            if re.search(pat, text, re.IGNORECASE):
                self.is_income_flag = True
                break

        # Remove known prefixes
        for pat in PREFIX_PATTERNS:
            text = re.sub(pat, "", text, flags=re.IGNORECASE)

        # Remove card masks
        text = re.sub(CARD_MASK_PATTERN, " ", text, flags=re.IGNORECASE)

        # Remove phone numbers
        text = re.sub(PHONE_PATTERN, " ", text)

        # Remove store numbers
        text = re.sub(STORE_NUM_PATTERN, " ", text, flags=re.IGNORECASE)

        # Remove trailing dates
        text = re.sub(DATE_PATTERN, " ", text)

        # Remove state/zip suffixes and international location codes
        text = re.sub(US_STATE_ZIP_PATTERN, " ", text)
        text = re.sub(INTL_LOCATIONS, " ", text)

        # Extract domain if present
        domain_match = re.search(URL_PATTERN, text, re.IGNORECASE)
        if domain_match:
            self.meta["domain"] = domain_match.group(1).lower()

        # Remove remaining special symbols but keep letters, digits, and spaces
        cleaned = re.sub(r"[^\w\s-]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        self.cleaned = cleaned
        self.tokens = [t for t in re.split(r"[\s-]+", cleaned) if len(t) > 1]

        # Extract candidate merchant (first 1 to 3 words)
        if self.tokens:
            self.clean_merchant = " ".join(self.tokens[:3])
        else:
            self.clean_merchant = self.raw.strip()


def normalize_description(raw: str) -> NormalizedDescription:
    return NormalizedDescription(raw)
