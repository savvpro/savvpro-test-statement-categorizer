"""Default merchant and pattern rules for transaction categorization.

Defines deterministic rules tailored for freelancers and software developers.
Rules are prioritized and define expected direction, match patterns, and human-readable explanations.
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import List, Optional

from app.schemas.category import DefaultCategory


class MatchType(str, Enum):
    """Rule matching strategy."""

    EXACT = "EXACT"
    CONTAINS = "CONTAINS"
    REGEX = "REGEX"


@dataclass(frozen=True)
class MerchantRule:
    """A deterministic classification rule."""

    id: str
    pattern: str
    category: str
    match_type: MatchType
    confidence: float
    explanation: str
    priority: int = 100
    expected_direction: Optional[str] = "negative"  # "negative", "positive", or "any"

    def matches(self, normalized_text: str) -> bool:
        """Check if this rule matches the normalized description string."""
        if not normalized_text:
            return False

        if self.match_type == MatchType.EXACT:
            return normalized_text == self.pattern

        if self.match_type == MatchType.CONTAINS:
            return self.pattern in normalized_text

        if self.match_type == MatchType.REGEX:
            return bool(re.search(self.pattern, normalized_text, re.IGNORECASE))

        return False


# Curated default rules for independent software developers and freelancers.
DEFAULT_MERCHANT_RULES: List[MerchantRule] = [
    # -------------------------------------------------------------
    # Business Income (Requires Positive Direction) - Priority 130
    # -------------------------------------------------------------
    MerchantRule(
        id="inc-client-payment",
        pattern=r"\b(CLIENT PAYMENT|INVOICE PAYMENT|CONSULTING (?:PAYMENT|FEE|RETAINER)|FREELANCE (?:CONTRACTOR PMT|PAYMENT)|CLIENT DIRECT DEP)\b",
        category=DefaultCategory.BUSINESS_INCOME.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Explicit client freelance payment or invoice deposit identified.",
        priority=130,
        expected_direction="positive",
    ),
    MerchantRule(
        id="inc-invoice-num",
        pattern=r"\bINVOICE\s*#?\s*\d+\b",
        category=DefaultCategory.BUSINESS_INCOME.value,
        match_type=MatchType.REGEX,
        confidence=0.90,
        explanation="Client invoice settlement reference detected.",
        priority=125,
        expected_direction="positive",
    ),

    # -------------------------------------------------------------
    # Cloud Hosting Services - Priority 120
    # -------------------------------------------------------------
    MerchantRule(
        id="cloud-aws-explicit",
        pattern=r"\b(AWS(?:\*BILLING|\.AMAZON|\s+CLOUD)?|AMAZON WEB SERVICES)\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (Amazon Web Services / AWS).",
        priority=120,
    ),
    MerchantRule(
        id="cloud-digitalocean",
        pattern=r"\bDIGITALOCEAN\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (DigitalOcean).",
        priority=120,
    ),
    MerchantRule(
        id="cloud-heroku",
        pattern=r"\bHEROKU\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (Heroku).",
        priority=120,
    ),
    MerchantRule(
        id="cloud-vercel",
        pattern=r"\bVERCEL\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (Vercel).",
        priority=120,
    ),
    MerchantRule(
        id="cloud-cloudflare",
        pattern=r"\bCLOUDFLARE\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (Cloudflare).",
        priority=120,
    ),
    MerchantRule(
        id="cloud-gcp",
        pattern=r"\b(GOOGLE CLOUD|GCP\*CLOUD)\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (Google Cloud Platform).",
        priority=120,
    ),
    MerchantRule(
        id="cloud-linode",
        pattern=r"\bLINODE\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (Linode).",
        priority=120,
    ),
    MerchantRule(
        id="cloud-hetzner",
        pattern=r"\bHETZNER\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (Hetzner).",
        priority=120,
    ),
    MerchantRule(
        id="cloud-synthetic-cloudhost",
        pattern=r"\bCLOUDHOST\b",
        category=DefaultCategory.CLOUD_HOSTING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known cloud hosting merchant pattern matched (CloudHost).",
        priority=120,
    ),

    # -------------------------------------------------------------
    # Developer Software & SaaS - Priority 110
    # -------------------------------------------------------------
    MerchantRule(
        id="soft-github",
        pattern=r"\b(GITHUB|GITHUB-COPILOT|GITHUB\.COM)\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (GitHub).",
        priority=110,
    ),
    MerchantRule(
        id="soft-jetbrains",
        pattern=r"\bJETBRAINS\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (JetBrains).",
        priority=110,
    ),
    MerchantRule(
        id="soft-docker",
        pattern=r"\b(DOCKER|DOCKER INC)\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (Docker).",
        priority=110,
    ),
    MerchantRule(
        id="soft-openai",
        pattern=r"\b(OPENAI|CHATGPT|OPENAI API)\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (OpenAI).",
        priority=110,
    ),
    MerchantRule(
        id="soft-figma",
        pattern=r"\bFIGMA\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (Figma).",
        priority=110,
    ),
    MerchantRule(
        id="soft-atlassian",
        pattern=r"\b(ATLASSIAN|JIRA|CONFLUENCE)\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (Atlassian / Jira).",
        priority=110,
    ),
    MerchantRule(
        id="soft-slack",
        pattern=r"\bSLACK\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (Slack).",
        priority=110,
    ),
    MerchantRule(
        id="soft-cursor",
        pattern=r"\b(CURSOR\.SH|CURSOR AI|CURSOR SUBSCRIPTION)\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (Cursor).",
        priority=110,
    ),
    MerchantRule(
        id="soft-adobe",
        pattern=r"\b(ADOBE|ADOBE CREATIVE CLOUD)\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software merchant pattern matched (Adobe Creative Cloud).",
        priority=110,
    ),
    MerchantRule(
        id="soft-generic-ide",
        pattern=r"\bIDE SOFTWARE SUBSCRIPTION\b",
        category=DefaultCategory.SOFTWARE.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known developer software subscription pattern matched.",
        priority=110,
    ),

    # -------------------------------------------------------------
    # Advertising & Marketing - Priority 108
    # -------------------------------------------------------------
    MerchantRule(
        id="ad-google",
        pattern=r"\b(GOOGLE ADS|GOOGLE ADWORDS)\b",
        category=DefaultCategory.ADVERTISING_AND_MARKETING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known advertising merchant pattern matched (Google Ads).",
        priority=108,
    ),
    MerchantRule(
        id="ad-meta",
        pattern=r"\b(META ADS|FACEBOOK ADS|FB\.ME/ADS)\b",
        category=DefaultCategory.ADVERTISING_AND_MARKETING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known advertising merchant pattern matched (Meta / Facebook Ads).",
        priority=108,
    ),
    MerchantRule(
        id="ad-linkedin",
        pattern=r"\bLINKEDIN ADS\b",
        category=DefaultCategory.ADVERTISING_AND_MARKETING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known advertising merchant pattern matched (LinkedIn Ads).",
        priority=108,
    ),
    MerchantRule(
        id="ad-twitter",
        pattern=r"\b(TWITTER ADS|X ADS)\b",
        category=DefaultCategory.ADVERTISING_AND_MARKETING.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known advertising merchant pattern matched (Twitter / X Ads).",
        priority=108,
    ),

    # -------------------------------------------------------------
    # Internet & Telecommunications - Priority 105
    # -------------------------------------------------------------
    MerchantRule(
        id="telecom-comcast",
        pattern=r"\b(COMCAST|XFINITY)\b",
        category=DefaultCategory.INTERNET_AND_TELECOM.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known internet service provider pattern matched (Comcast / Xfinity).",
        priority=105,
    ),
    MerchantRule(
        id="telecom-att",
        pattern=r"\b(AT&T|ATT BILL PAYMENT)\b",
        category=DefaultCategory.INTERNET_AND_TELECOM.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known telecommunications provider pattern matched (AT&T).",
        priority=105,
    ),
    MerchantRule(
        id="telecom-verizon",
        pattern=r"\bVERIZON\b",
        category=DefaultCategory.INTERNET_AND_TELECOM.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known telecommunications provider pattern matched (Verizon).",
        priority=105,
    ),
    MerchantRule(
        id="telecom-spectrum",
        pattern=r"\b(SPECTRUM|CHARTER COMM)\b",
        category=DefaultCategory.INTERNET_AND_TELECOM.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known internet service provider pattern matched (Spectrum).",
        priority=105,
    ),
    MerchantRule(
        id="telecom-starlink",
        pattern=r"\bSTARLINK\b",
        category=DefaultCategory.INTERNET_AND_TELECOM.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known internet service provider pattern matched (Starlink).",
        priority=105,
    ),
    MerchantRule(
        id="telecom-generic-bill",
        pattern=r"\b(INTERNET BILL|INTERNET SERVICE|FIBER INTERNET)\b",
        category=DefaultCategory.INTERNET_AND_TELECOM.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Known internet telecommunications expense pattern matched.",
        priority=105,
    ),

    # -------------------------------------------------------------
    # Bank Fees - Priority 105
    # -------------------------------------------------------------
    MerchantRule(
        id="bank-fee-service",
        pattern=r"\b(MONTHLY SERVICE FEE|MAINTENANCE FEE|ACCOUNT SERVICE CHARGE|WIRE TRANSFER FEE|OVERDRAFT FEE|FOREIGN TRANSACTION FEE|ATM SURCHARGE FEE|INSUFFICIENT FUNDS FEE)\b",
        category=DefaultCategory.BANK_FEES.value,
        match_type=MatchType.REGEX,
        confidence=0.95,
        explanation="Recognized banking service fee pattern matched.",
        priority=105,
    ),

    # -------------------------------------------------------------
    # Professional Services - Priority 100
    # -------------------------------------------------------------
    MerchantRule(
        id="prof-accounting",
        pattern=r"\b(CPA ACCOUNTING|TAX CONSULTING|BOOKKEEPING SERVICES|LEGALZOOM)\b",
        category=DefaultCategory.PROFESSIONAL_SERVICES.value,
        match_type=MatchType.REGEX,
        confidence=0.90,
        explanation="Recognized professional legal or accounting service matched.",
        priority=100,
    ),

    # -------------------------------------------------------------
    # Hardware & Equipment - Priority 100
    # -------------------------------------------------------------
    MerchantRule(
        id="hw-stores",
        pattern=r"\b(MICRO CENTER|DELL COMPUTERS|APPLE STORE)\b",
        category=DefaultCategory.HARDWARE_AND_EQUIPMENT.value,
        match_type=MatchType.REGEX,
        confidence=0.90,
        explanation="Known computer hardware and equipment retailer pattern matched.",
        priority=100,
    ),

    # -------------------------------------------------------------
    # Office Supplies - Priority 100
    # -------------------------------------------------------------
    MerchantRule(
        id="off-supplies",
        pattern=r"\b(STAPLES|OFFICE DEPOT|OFFICEMAX)\b",
        category=DefaultCategory.OFFICE_SUPPLIES.value,
        match_type=MatchType.REGEX,
        confidence=0.90,
        explanation="Known office supplies retailer pattern matched.",
        priority=100,
    ),

    # -------------------------------------------------------------
    # Meals - Priority 95 (Evaluated before general travel)
    # -------------------------------------------------------------
    MerchantRule(
        id="meal-delivery",
        pattern=r"\b(UBER EATS|UBEREATS|DOORDASH|GRUBHUB)\b",
        category=DefaultCategory.MEALS.value,
        match_type=MatchType.REGEX,
        confidence=0.90,
        explanation="Known meal or food delivery service pattern matched.",
        priority=95,
    ),
    MerchantRule(
        id="meal-cafes",
        pattern=r"\b(STARBUCKS|JOE'?S CAFE)\b",
        category=DefaultCategory.MEALS.value,
        match_type=MatchType.REGEX,
        confidence=0.90,
        explanation="Known cafe or dining establishment pattern matched.",
        priority=95,
    ),

    # -------------------------------------------------------------
    # Travel - Priority 90
    # -------------------------------------------------------------
    MerchantRule(
        id="travel-rideshare",
        pattern=r"\b(UBER\s*\*TRIP|LYFT\s*\*RIDE|AMTRAK|DELTA AIR|UNITED AIRLINES)\b",
        category=DefaultCategory.TRAVEL.value,
        match_type=MatchType.REGEX,
        confidence=0.90,
        explanation="Known business travel or transportation merchant pattern matched.",
        priority=90,
    ),
]
