"""
Categorization rules, high-confidence vendor mappings, mixed-use vendor flags,
and meal keyword patterns for freelance software engineers and tech consultants.
"""

from typing import Dict, Any, List

# Tier 1: High Confidence Vendors (0.95 - 0.99 confidence)
# Deterministic mappings that auto-verify with no manual review needed.
HIGH_CONFIDENCE_VENDORS: Dict[str, Dict[str, Any]] = {
    # Software & Cloud Subscriptions (Part V - Software)
    "AWS": {
        "category": "Software & Subscriptions",
        "confidence": 0.99,
        "rule": "High-confidence developer cloud infrastructure (AWS)",
    },
    "AMAZON WEB SERVICES": {
        "category": "Software & Subscriptions",
        "confidence": 0.99,
        "rule": "High-confidence developer cloud infrastructure (AWS)",
    },
    "GITHUB": {
        "category": "Software & Subscriptions",
        "confidence": 0.99,
        "rule": "High-confidence code hosting and CI/CD (GitHub)",
    },
    "VERCEL": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence frontend hosting platform (Vercel)",
    },
    "HEROKU": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence PaaS cloud platform (Heroku)",
    },
    "DIGITALOCEAN": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence cloud hosting provider (DigitalOcean)",
    },
    "JETBRAINS": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence IDE tool license (JetBrains)",
    },
    "OPENAI": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence AI API / ChatGPT subscription (OpenAI)",
    },
    "ANTHROPIC": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence AI API subscription (Anthropic)",
    },
    "ADOBE": {
        "category": "Software & Subscriptions",
        "confidence": 0.96,
        "rule": "High-confidence creative suite software (Adobe)",
    },
    "FIGMA": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence UI/UX design software (Figma)",
    },
    "SLACK": {
        "category": "Software & Subscriptions",
        "confidence": 0.97,
        "rule": "High-confidence team communication tool (Slack)",
    },
    "NOTION": {
        "category": "Software & Subscriptions",
        "confidence": 0.97,
        "rule": "High-confidence workspace and documentation SaaS (Notion)",
    },
    "ZOOM": {
        "category": "Software & Subscriptions",
        "confidence": 0.97,
        "rule": "High-confidence video conferencing SaaS (Zoom)",
    },
    "1PASSWORD": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence security/password manager SaaS (1Password)",
    },
    "DATADOG": {
        "category": "Software & Subscriptions",
        "confidence": 0.99,
        "rule": "High-confidence observability monitoring SaaS (Datadog)",
    },
    "SENTRY": {
        "category": "Software & Subscriptions",
        "confidence": 0.99,
        "rule": "High-confidence error tracking SaaS (Sentry)",
    },
    "DOCKER": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence container tooling SaaS (Docker)",
    },
    "SUPABASE": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence backend database platform (Supabase)",
    },
    "CLOUDFLARE": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence DNS / edge hosting SaaS (Cloudflare)",
    },
    "POSTMAN": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence API testing tool (Postman)",
    },
    "ATLASSIAN": {
        "category": "Software & Subscriptions",
        "confidence": 0.97,
        "rule": "High-confidence Jira / Confluence tooling (Atlassian)",
    },
    "LINEAR": {
        "category": "Software & Subscriptions",
        "confidence": 0.98,
        "rule": "High-confidence issue tracking SaaS (Linear)",
    },

    # Travel & Transportation (Line 24a / Line 9)
    "UBER": {
        "category": "Travel & Transportation",
        "confidence": 0.95,
        "rule": "High-confidence rideshare transit (Uber)",
    },
    "LYFT": {
        "category": "Travel & Transportation",
        "confidence": 0.95,
        "rule": "High-confidence rideshare transit (Lyft)",
    },
    "DELTA AIR": {
        "category": "Travel & Transportation",
        "confidence": 0.98,
        "rule": "High-confidence airline business travel (Delta)",
    },
    "DELTA": {
        "category": "Travel & Transportation",
        "confidence": 0.96,
        "rule": "High-confidence airline business travel (Delta)",
    },
    "UNITED AIRLINES": {
        "category": "Travel & Transportation",
        "confidence": 0.98,
        "rule": "High-confidence airline business travel (United)",
    },
    "AMERICAN AIRLINES": {
        "category": "Travel & Transportation",
        "confidence": 0.98,
        "rule": "High-confidence airline business travel (American Airlines)",
    },
    "ALASKA AIRLINES": {
        "category": "Travel & Transportation",
        "confidence": 0.98,
        "rule": "High-confidence airline business travel (Alaska Airlines)",
    },
    "AMTRAK": {
        "category": "Travel & Transportation",
        "confidence": 0.97,
        "rule": "High-confidence passenger rail travel (Amtrak)",
    },
    "AIRBNB": {
        "category": "Travel & Transportation",
        "confidence": 0.95,
        "rule": "High-confidence travel accommodation (Airbnb)",
    },
    "MARRIOTT": {
        "category": "Travel & Transportation",
        "confidence": 0.97,
        "rule": "High-confidence hotel lodging (Marriott)",
    },
    "HILTON": {
        "category": "Travel & Transportation",
        "confidence": 0.97,
        "rule": "High-confidence hotel lodging (Hilton)",
    },

    # Internet & Utilities (Line 25 - 80% standard business allocation)
    "COMCAST": {
        "category": "Internet & Utilities",
        "confidence": 0.96,
        "rule": "Home office broadband internet (Comcast - 80% deductible)",
    },
    "XFINITY": {
        "category": "Internet & Utilities",
        "confidence": 0.96,
        "rule": "Home office broadband internet (Xfinity - 80% deductible)",
    },
    "VERIZON": {
        "category": "Internet & Utilities",
        "confidence": 0.96,
        "rule": "Business mobile and internet service (Verizon - 80% deductible)",
    },
    "AT&T": {
        "category": "Internet & Utilities",
        "confidence": 0.96,
        "rule": "Business mobile and fiber internet (AT&T - 80% deductible)",
    },
    "T-MOBILE": {
        "category": "Internet & Utilities",
        "confidence": 0.96,
        "rule": "Business cellular mobile connectivity (T-Mobile - 80% deductible)",
    },
    "SPECTRUM": {
        "category": "Internet & Utilities",
        "confidence": 0.95,
        "rule": "Office internet connectivity (Spectrum - 80% deductible)",
    },
    "GOOGLE FIBER": {
        "category": "Internet & Utilities",
        "confidence": 0.96,
        "rule": "Home office gigabit fiber (Google Fiber - 80% deductible)",
    },

    # Advertising & Marketing (Line 8)
    "GOOGLE ADS": {
        "category": "Advertising & Marketing",
        "confidence": 0.98,
        "rule": "Digital client acquisition advertising (Google Ads)",
    },
    "META ADS": {
        "category": "Advertising & Marketing",
        "confidence": 0.98,
        "rule": "Digital social advertising (Meta Ads)",
    },
    "FACEBOOK ADS": {
        "category": "Advertising & Marketing",
        "confidence": 0.98,
        "rule": "Digital social advertising (Facebook Ads)",
    },
    "LINKEDIN ADS": {
        "category": "Advertising & Marketing",
        "confidence": 0.98,
        "rule": "B2B client acquisition advertising (LinkedIn Ads)",
    },
    "NAMECHEAP": {
        "category": "Advertising & Marketing",
        "confidence": 0.97,
        "rule": "Client and product domain registration (Namecheap)",
    },
    "GODADDY": {
        "category": "Advertising & Marketing",
        "confidence": 0.96,
        "rule": "Domain registration and DNS hosting (GoDaddy)",
    },

    # Professional & Legal Services (Line 17)
    "STRIPE FEE": {
        "category": "Professional & Legal Services",
        "confidence": 0.99,
        "rule": "Merchant processing fee deduction (Stripe)",
    },
    "STRIPE PROCESSING": {
        "category": "Professional & Legal Services",
        "confidence": 0.99,
        "rule": "Merchant processing fee deduction (Stripe)",
    },
    "LEGALZOOM": {
        "category": "Professional & Legal Services",
        "confidence": 0.97,
        "rule": "Corporate compliance and legal entity filing (LegalZoom)",
    },
    "GUSTO": {
        "category": "Professional & Legal Services",
        "confidence": 0.97,
        "rule": "Payroll processing and HR compliance service (Gusto)",
    },
    "DELAWARE CORP": {
        "category": "Professional & Legal Services",
        "confidence": 0.98,
        "rule": "State franchise tax and registered agent service",
    },
    "CLERKY": {
        "category": "Professional & Legal Services",
        "confidence": 0.98,
        "rule": "Startup corporate legal documents (Clerky)",
    },

    # Specialized Hardware vendors (Line 13)
    "MICRO CENTER": {
        "category": "Hardware & Equipment",
        "confidence": 0.88,
        "rule": "Dedicated computer hardware & component retailer",
    },
    "SYSTEM76": {
        "category": "Hardware & Equipment",
        "confidence": 0.96,
        "rule": "Dedicated Linux workstation hardware (System76)",
    },
    "FRAMEWORK": {
        "category": "Hardware & Equipment",
        "confidence": 0.95,
        "rule": "Modular laptop computer hardware (Framework)",
    },
    "KEYCHRON": {
        "category": "Hardware & Equipment",
        "confidence": 0.92,
        "rule": "Ergonomic developer keyboard hardware (Keychron)",
    },

    # Specialized Books & Professional Development (Line 22)
    "O REILLY": {
        "category": "Office Supplies & Books",
        "confidence": 0.96,
        "rule": "Technical computing literature and learning (O'Reilly)",
    },
    "PRAGMATIC BOOKSHELF": {
        "category": "Office Supplies & Books",
        "confidence": 0.97,
        "rule": "Software engineering technical books",
    },
    "MANNING": {
        "category": "Office Supplies & Books",
        "confidence": 0.96,
        "rule": "Technical computer science book publication",
    },
}

# Tier 2: Mixed-Use Vendors (Confidence 0.40 - 0.70)
# Known vendors that frequently mix business and personal expenses.
# Require manual review flag for IRS compliance safety.
MIXED_USE_VENDORS: Dict[str, Dict[str, Any]] = {
    "AMAZON": {
        "suggested_category": "Office Supplies & Books",
        "confidence": 0.65,
        "reason": "Mixed personal vs business purchases. Confirm whether order is business electronics/books or personal household items.",
    },
    "APPLE": {
        "suggested_category": "Hardware & Equipment",
        "confidence": 0.68,
        "reason": "Verify if charge is business workstation hardware vs personal App Store subscription or media.",
    },
    "BEST BUY": {
        "suggested_category": "Hardware & Equipment",
        "confidence": 0.60,
        "reason": "Retailer carries both business monitors/peripherals and consumer home entertainment.",
    },
    "TARGET": {
        "suggested_category": "Office Supplies & Books",
        "confidence": 0.40,
        "reason": "Department store. Highly likely personal household purchase unless dedicated office supplies.",
    },
    "WALMART": {
        "suggested_category": "Office Supplies & Books",
        "confidence": 0.40,
        "reason": "General retail merchant. High risk of personal non-deductible items.",
    },
    "COSTCO": {
        "suggested_category": "Office Supplies & Books",
        "confidence": 0.45,
        "reason": "Wholesale club. Verify business office supplies vs personal grocery/household items.",
    },
    "IKEA": {
        "suggested_category": "Office Supplies & Books",
        "confidence": 0.55,
        "reason": "Furniture retailer. Verify if dedicated home office workstation/desk.",
    },
}

# Tier 3: Meal & Dining Keywords
MEAL_PATTERNS: List[str] = [
    r"\bCAFE\b",
    r"\bCOFFEE\b",
    r"\bSTARBUCKS\b",
    r"\bRESTAURANT\b",
    r"\bPIZZA\b",
    r"\bDOORDASH\b",
    r"\bUBER\s+EATS\b",
    r"\bGRUBHUB\b",
    r"\bCHIPOTLE\b",
    r"\bSWEETGREEN\b",
    r"\bDELI\b",
    r"\bBAKERY\b",
    r"\bBISTRO\b",
    r"\bDINER\b",
    r"\bSUSHI\b",
    r"\bBURGER\b",
    r"\bPANERA\b",
    r"\bPEETS\b",
    r"\bBLUE\s+BOTTLE\b",
    r"\bESPRESSO\b",
    r"\bKITCHEN\b",
    r"\bTAQUERIA\b",
    r"\bBREWERY\b",
    r"\bBAR\b",
]

# Established national food chains that can be auto-approved at meals category (still 50% deductible)
AUTO_VERIFIED_MEAL_CHAINS = {
    "STARBUCKS", "CHIPOTLE", "SWEETGREEN", "PANERA", "DOORDASH",
    "UBER EATS", "GRUBHUB", "PEETS", "BLUE BOTTLE"
}
