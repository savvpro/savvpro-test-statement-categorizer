import re

# Standard Tax Categories for Freelance Software Engineer / Small Business
CATEGORIES = [
    "Software & Subscriptions",
    "Cloud & Infrastructure",
    "Hardware & Office Equipment",
    "Internet & Utilities",
    "Professional & Legal Services",
    "Bank & Merchant Fees",
    "Travel & Transportation",
    "Meals & Client Entertainment",
    "Advertising & Marketing",
    "Client Income & Revenue",
    "Transfers & Card Payments",
    "Needs Review",
]

# Exact Merchant Mapping: Normalized Merchant String -> (Category, Confidence)
EXACT_MERCHANTS: dict[str, tuple[str, float]] = {
    # Software & Developer Tools
    "GITHUB": ("Software & Subscriptions", 0.98),
    "GITHUB INC": ("Software & Subscriptions", 0.98),
    "GITLAB": ("Software & Subscriptions", 0.98),
    "BITBUCKET": ("Software & Subscriptions", 0.98),
    "JETBRAINS": ("Software & Subscriptions", 0.98),
    "SLACK": ("Software & Subscriptions", 0.98),
    "FIGMA": ("Software & Subscriptions", 0.98),
    "NOTION": ("Software & Subscriptions", 0.98),
    "1PASSWORD": ("Software & Subscriptions", 0.98),
    "ZOOM": ("Software & Subscriptions", 0.98),
    "ZOOM.US": ("Software & Subscriptions", 0.98),
    "POSTMAN": ("Software & Subscriptions", 0.98),
    "ADOBE": ("Software & Subscriptions", 0.98),
    "ADOBE CREATIVE CLOUD": ("Software & Subscriptions", 0.98),
    "LINEAR": ("Software & Subscriptions", 0.98),
    "RAYCAST": ("Software & Subscriptions", 0.98),
    "CURSOR": ("Software & Subscriptions", 0.98),
    "SUBSTACK": ("Software & Subscriptions", 0.95),
    "ATLASSIAN": ("Software & Subscriptions", 0.98),
    "DATADOG": ("Software & Subscriptions", 0.98),
    "SENTRY": ("Software & Subscriptions", 0.98),
    "MIRO": ("Software & Subscriptions", 0.98),
    "LOOM": ("Software & Subscriptions", 0.98),
    "CANVA": ("Software & Subscriptions", 0.98),
    "MICROSOFT": ("Software & Subscriptions", 0.95),
    "MSFT 365": ("Software & Subscriptions", 0.98),

    # Cloud & Hosting Infrastructure
    "AWS": ("Cloud & Infrastructure", 0.98),
    "AMAZON WEB SERVICES": ("Cloud & Infrastructure", 0.98),
    "GOOGLE CLOUD": ("Cloud & Infrastructure", 0.98),
    "GCP": ("Cloud & Infrastructure", 0.98),
    "DIGITALOCEAN": ("Cloud & Infrastructure", 0.98),
    "VERCEL": ("Cloud & Infrastructure", 0.98),
    "NETLIFY": ("Cloud & Infrastructure", 0.98),
    "HEROKU": ("Cloud & Infrastructure", 0.98),
    "RENDER": ("Cloud & Infrastructure", 0.98),
    "FLY.IO": ("Cloud & Infrastructure", 0.98),
    "CLOUDFLARE": ("Cloud & Infrastructure", 0.98),
    "HETZNER": ("Cloud & Infrastructure", 0.98),
    "LINODE": ("Cloud & Infrastructure", 0.98),
    "SUPABASE": ("Cloud & Infrastructure", 0.98),
    "MONGODB ATLAS": ("Cloud & Infrastructure", 0.98),
    "PLANETSCALE": ("Cloud & Infrastructure", 0.98),
    "NAMECHEAP": ("Cloud & Infrastructure", 0.98),
    "PORKBUN": ("Cloud & Infrastructure", 0.98),
    "GODADDY": ("Cloud & Infrastructure", 0.95),

    # Hardware & Office Equipment
    "APPLE": ("Hardware & Office Equipment", 0.95),
    "APPLE STORE": ("Hardware & Office Equipment", 0.98),
    "BEST BUY": ("Hardware & Office Equipment", 0.95),
    "DELL": ("Hardware & Office Equipment", 0.98),
    "LENOVO": ("Hardware & Office Equipment", 0.98),
    "KEYCHRON": ("Hardware & Office Equipment", 0.98),
    "B&H PHOTO": ("Hardware & Office Equipment", 0.95),
    "NEW EGG": ("Hardware & Office Equipment", 0.95),
    "MICRO CENTER": ("Hardware & Office Equipment", 0.98),
    "LOGITECH": ("Hardware & Office Equipment", 0.98),
    "STAPLES": ("Hardware & Office Equipment", 0.95),

    # Internet & Utilities
    "COMCAST": ("Internet & Utilities", 0.98),
    "XFINITY": ("Internet & Utilities", 0.98),
    "VERIZON": ("Internet & Utilities", 0.98),
    "AT&T": ("Internet & Utilities", 0.98),
    "SPECTRUM": ("Internet & Utilities", 0.98),
    "T-MOBILE": ("Internet & Utilities", 0.98),
    "STARLINK": ("Internet & Utilities", 0.98),
    "GOOGLE FIBER": ("Internet & Utilities", 0.98),

    # Professional & Legal Services
    "GUSTO": ("Professional & Legal Services", 0.98),
    "DEEL": ("Professional & Legal Services", 0.98),
    "RIPPLING": ("Professional & Legal Services", 0.98),
    "UPWORK": ("Professional & Legal Services", 0.95),
    "FIVERR": ("Professional & Legal Services", 0.95),
    "TURBOTAX": ("Professional & Legal Services", 0.98),
    "INTUIT QUICKBOOKS": ("Professional & Legal Services", 0.98),
    "QUICKBOOKS": ("Professional & Legal Services", 0.98),
    "LEGALZOOM": ("Professional & Legal Services", 0.98),
    "CLERKY": ("Professional & Legal Services", 0.98),

    # Bank & Merchant Fees
    "BANK OF AMERICA WIRE FEE": ("Bank & Merchant Fees", 0.98),
    "CHASE WIRE FEE": ("Bank & Merchant Fees", 0.98),
    "MONTHLY MAINTENANCE FEE": ("Bank & Merchant Fees", 0.98),
    "SERVICE CHARGE": ("Bank & Merchant Fees", 0.95),
    "FOREIGN TRANSACTION FEE": ("Bank & Merchant Fees", 0.98),
    "FX FEE": ("Bank & Merchant Fees", 0.98),
    "OVERDRAFT FEE": ("Bank & Merchant Fees", 0.98),
    "ATM SURCHARGE": ("Bank & Merchant Fees", 0.95),

    # Travel & Transportation
    "UBER": ("Travel & Transportation", 0.95),
    "UBER TRIP": ("Travel & Transportation", 0.98),
    "LYFT": ("Travel & Transportation", 0.98),
    "DELTA AIR": ("Travel & Transportation", 0.98),
    "UNITED AIRLINES": ("Travel & Transportation", 0.98),
    "AMERICAN AIRLINES": ("Travel & Transportation", 0.98),
    "AIRBNB": ("Travel & Transportation", 0.95),
    "AMTRAK": ("Travel & Transportation", 0.98),
    "ALASKA AIR": ("Travel & Transportation", 0.98),

    # Advertising & Marketing
    "GOOGLE ADS": ("Advertising & Marketing", 0.98),
    "FACEBOOK ADS": ("Advertising & Marketing", 0.98),
    "META ADS": ("Advertising & Marketing", 0.98),
    "LINKEDIN ADS": ("Advertising & Marketing", 0.98),
    "TWITTER ADS": ("Advertising & Marketing", 0.98),
    "REDDIT ADS": ("Advertising & Marketing", 0.98),
    "MAILCHIMP": ("Advertising & Marketing", 0.98),
}

# Regex and Keyword Rules: Pattern -> (Category, Confidence, Reason)
PATTERN_RULES: list[tuple[re.Pattern, str, float, str]] = [
    # Transfers & Credit Card Payments (High priority)
    (
        re.compile(
            r"\b(?:TRANSFER (?:TO|FROM)|AUTOPAY|PAYMENT THANK YOU|CREDIT CARD PAYMENT|"
            r"INTERNET TRANSFER|ONLINE TRANSFER|MOBILE TRANSFER|ZELLE (?:TO|FROM)|"
            r"WIRE (?:OUT|IN)|INTERNAL TRANSFER|SAVINGS TRANSFER)\b",
            re.IGNORECASE,
        ),
        "Transfers & Card Payments",
        0.98,
        "Pattern match: Internal account transfer or credit card payment",
    ),
    # Client Income & Payouts (for credit rows)
    (
        re.compile(
            r"\b(?:STRIPE PAYOUT|PAYPAL PAYOUT|CLIENT INVOICE|CONSULTING FEE|DIRECT DEP - STRIPE|"
            r"PAYROLL DEPOSIT|INVOICE PAYMENT|ACH DEPOSIT)\b",
            re.IGNORECASE,
        ),
        "Client Income & Revenue",
        0.95,
        "Pattern match: Client income or merchant processor payout",
    ),
    # Bank & Foreign Exchange Fees
    (
        re.compile(
            r"\b(?:FOREIGN (?:TRANSACTION|EXCHANGE|CURRENCY) FEE|INTL (?:TXN|TRANS) FEE|"
            r"FX FEE|CROSS BORDER FEE|MONTHLY (?:SERVICE|MAINTENANCE) FEE|WIRE TRANSFER FEE|"
            r"OVERDRAFT CHARGE|NON-SUFFICIENT FUNDS|NSF FEE)\b",
            re.IGNORECASE,
        ),
        "Bank & Merchant Fees",
        0.98,
        "Pattern match: Bank, merchant, or foreign currency fee",
    ),
    # Cloud & Infrastructure
    (
        re.compile(
            r"\b(?:AWS\.AMAZON|AMAZON WEB SERVICES|GOOGLE CLOUD|GCP CLOUD|CLOUDFLARE|"
            r"DIGITALOCEAN|HEROKU|VERCEL|NETLIFY|SUPABASE|FLY\.IO|RENDER\.COM|HETZNER|LINODE)\b",
            re.IGNORECASE,
        ),
        "Cloud & Infrastructure",
        0.95,
        "Pattern match: Cloud hosting and server infrastructure",
    ),
    # Software & SaaS
    (
        re.compile(
            r"\b(?:GITHUB|GITLAB|BITBUCKET|JETBRAINS|ATLASSIAN|JIRA|CONFLUENCE|SLACK|"
            r"FIGMA|NOTION|1PASSWORD|ZOOM\.US|POSTMAN|ADOBE|LINEAR APP|RAYCAST|"
            r"CANVA|LOOM|SENTRY\.IO|DATADOG|MAILCHIMP|SENDGRID)\b",
            re.IGNORECASE,
        ),
        "Software & Subscriptions",
        0.95,
        "Pattern match: Developer tools and SaaS subscriptions",
    ),
    # Internet, Utilities & Telephony
    (
        re.compile(
            r"\b(?:COMCAST|XFINITY|VERIZON|AT&T|SPECTRUM|T-MOBILE|STARLINK|GOOGLE FIBER|CENTURYLINK)\b",
            re.IGNORECASE,
        ),
        "Internet & Utilities",
        0.95,
        "Pattern match: Internet, telecommunications, and office utilities",
    ),
    # Travel & Rideshare
    (
        re.compile(
            r"\b(?:UBER(?:\s*\*TRIP|\s+TRIP|\s+RIDES)?|LYFT|DELTA AIR|UNITED AIRLINES|"
            r"AMERICAN AIRLINES|SOUTHWEST AIR|AIRBNB|HOTEL|AMTRAK)\b",
            re.IGNORECASE,
        ),
        "Travel & Transportation",
        0.92,
        "Pattern match: Business travel and rideshare transportation",
    ),
    # Hardware & Electronics
    (
        re.compile(
            r"\b(?:APPLE STORE|BEST BUY|B&H PHOTO|NEWEGG|MICRO CENTER|KEYCHRON|DELL TECHNOLOGIES)\b",
            re.IGNORECASE,
        ),
        "Hardware & Office Equipment",
        0.92,
        "Pattern match: Computer hardware and electronics equipment",
    ),
    # Professional Services & Payroll
    (
        re.compile(
            r"\b(?:GUSTO PAYROLL|DEEL|RIPPLING|TURBOTAX|QUICKBOOKS|INTUIT|LEGALZOOM|CLERKY)\b",
            re.IGNORECASE,
        ),
        "Professional & Legal Services",
        0.95,
        "Pattern match: Legal, accounting, and payroll services",
    ),
    # Advertising & Marketing
    (
        re.compile(
            r"\b(?:GOOGLE\s*ADS|FACEBOOK\s*ADS|META\s*ADS|TWITTER\s*ADS|LINKEDIN\s*ADS|REDDIT\s*ADS)\b",
            re.IGNORECASE,
        ),
        "Advertising & Marketing",
        0.95,
        "Pattern match: Digital advertising and paid marketing",
    ),
]

# Canonical merchant list for fuzzy matching
CANONICAL_MERCHANTS: dict[str, str] = {
    "GITHUB": "Software & Subscriptions",
    "GITLAB": "Software & Subscriptions",
    "JETBRAINS": "Software & Subscriptions",
    "SLACK": "Software & Subscriptions",
    "FIGMA": "Software & Subscriptions",
    "NOTION": "Software & Subscriptions",
    "ZOOM": "Software & Subscriptions",
    "ADOBE": "Software & Subscriptions",
    "AWS": "Cloud & Infrastructure",
    "AMAZON WEB SERVICES": "Cloud & Infrastructure",
    "GOOGLE CLOUD": "Cloud & Infrastructure",
    "DIGITALOCEAN": "Cloud & Infrastructure",
    "VERCEL": "Cloud & Infrastructure",
    "NETLIFY": "Cloud & Infrastructure",
    "CLOUDFLARE": "Cloud & Infrastructure",
    "HEROKU": "Cloud & Infrastructure",
    "APPLE": "Hardware & Office Equipment",
    "BEST BUY": "Hardware & Office Equipment",
    "KEYCHRON": "Hardware & Office Equipment",
    "DELL": "Hardware & Office Equipment",
    "COMCAST": "Internet & Utilities",
    "VERIZON": "Internet & Utilities",
    "AT&T": "Internet & Utilities",
    "GUSTO": "Professional & Legal Services",
    "TURBOTAX": "Professional & Legal Services",
    "QUICKBOOKS": "Professional & Legal Services",
    "UBER": "Travel & Transportation",
    "LYFT": "Travel & Transportation",
    "AIRBNB": "Travel & Transportation",
    "DELTA": "Travel & Transportation",
}
