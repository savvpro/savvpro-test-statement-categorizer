"""
Deterministic Rule Definitions & Merchant Registries for Freelance/Sole-Proprietor Brain.
High-confidence patterns and canonical merchant dictionaries.
"""

from typing import List, Dict, Tuple
from app.brain.taxonomy import Category

# High-Confidence Deterministic Patterns (Regex, Category, Confidence, Match Reason)
HIGH_CONFIDENCE_RULES: List[Tuple[str, str, float, str]] = [
    # --- Software & SaaS Subscriptions (100% Tax Deductible) ---
    (r"\b(ADOBE|CREATIVE\s*CLOUD|PHOTOSHOP|ILLUSTRATOR)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized creative software suite (Adobe)."),
    (r"\b(FIGMA|CANVA|SKETCH)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized design & prototyping subscription."),
    (r"\b(GITHUB|GITLAB|BITBUCKET)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized developer code repository platform."),
    (r"\b(JETBRAINS|SUBLIME|VSCODE|CURSOR)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized IDE/developer tooling subscription."),
    (r"\b(AWS|AMAZON\s*WEB\s*SERVICES|DIGITALOCEAN|LINODE|VERCEL|NETLIFY|HEROKU|RENDER|SUPABASE)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized cloud hosting and infrastructure service."),
    (r"\b(OPENAI|CHATGPT|ANTHROPIC|CLAUDE|MIDJOURNEY|STABILITY\s*AI)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized AI developer API / assistant subscription."),
    (r"\b(GOOGLE\s*(?:WORKSPACE|CLOUD|STORAGE|GSUITE)|GSUITE)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized business productivity suite (Google Workspace)."),
    (r"\b(MICROSOFT\s*365|MSFT\s*\*?\s*365|OFFICE\s*365)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized office productivity software (Microsoft 365)."),
    (r"\b(ZOOM\.US|ZOOM\s*COMMUNICATIONS|SLACK\s*TECHNOLOGIES|SLACK)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized business communication & video conferencing tool."),
    (r"\b(NOTION|LINEAR|TRELLO|ASANA|MONDAY\.COM|CLICKUP|JIRA|ATLASSIAN)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized project management and documentation tool."),
    (r"\b(DROPBOX|BOX\.COM|1PASSWORD|BITWARDEN|LASTPASS)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized cloud storage or security utility."),
    (r"\b(WEBFLOW|SHOPIFY|WORDPRESS|SQUARESPACE|GHOST\.ORG)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized web publishing and CMS platform."),
    (r"\b(MAILCHIMP|SUBSTACK|SENDGRID|CONVERTKIT|LOOM|CALENDLY)\b", Category.SOFTWARE_SAAS, 0.98, "Recognized email automation or client booking tool."),

    # --- Travel & Transit (100% Tax Deductible away from home) ---
    (r"\b(UBER\s*\*?\s*TRIP|UBER|LYFT\s*\*?\s*RIDE|LYFT)\b", Category.TRAVEL_TRANSIT, 0.95, "Recognized rideshare business transit."),
    (r"\b(DELTA\s*AIR|UNITED\s*AIRLINES|AMERICAN\s*AIRLINES|SOUTHWEST\s*AIR|JETBLUE|ALASKA\s*AIR)\b", Category.TRAVEL_TRANSIT, 0.98, "Recognized commercial airline travel."),
    (r"\b(AIRBNB|HOTEL|MARRIOTT|HILTON|HYATT|SHERATON|WESTIN|HOLIDAY\s*INN)\b", Category.TRAVEL_TRANSIT, 0.98, "Recognized business lodging / accommodation."),
    (r"\b(HERTZ|ENTERPRISE\s*RENT|AVIS|BUDGET\s*RENT|NATIONAL\s*CAR)\b", Category.TRAVEL_TRANSIT, 0.98, "Recognized business car rental service."),
    (r"\b(AMTRAK|TRAIN|SUBWAY|METRO|MTA|BART|TRANSIT|TOLLWAY|EZPASS|FASTRAK)\b", Category.TRAVEL_TRANSIT, 0.95, "Recognized rail transit or highway toll."),

    # --- Equipment & Tech Hardware (Safe Harbor <$2500) ---
    (r"\b(APPLE\s*STORE|APPLE\.COM|B&H\s*PHOTO|MICRO\s*CENTER)\b", Category.EQUIPMENT_HARDWARE, 0.95, "Recognized hardware/electronics retailer for business equipment."),
    (r"\b(DELL|LENOVO|KEYCHRON|LOGITECH|FRAMEWORK\s*LAPTOP)\b", Category.EQUIPMENT_HARDWARE, 0.95, "Recognized computer hardware and peripheral vendor."),

    # --- Office Supplies & Workspace (100% Tax Deductible) ---
    (r"\b(WEWORK|REGUS|SPACES|INDUSTRIOUS)\b", Category.OFFICE_SUPPLIES, 0.98, "Recognized coworking space membership."),
    (r"\b(STAPLES|OFFICE\s*DEPOT|OFFICEMAX|PAPER\s*SOURCE)\b", Category.OFFICE_SUPPLIES, 0.95, "Recognized office stationery and supply vendor."),
    (r"\b(FEDEX\s*OFFICE|UPS\s*STORE|USPS\s*POST|STAMPS\.COM)\b", Category.OFFICE_SUPPLIES, 0.95, "Recognized postal shipping and business printing service."),

    # --- Advertising & Marketing (100% Tax Deductible) ---
    (r"\b(GOOGLE\s*\*?\s*ADS|GOOGLE\s*ADWORDS)\b", Category.ADVERTISING_MARKETING, 0.98, "Recognized search advertising platform (Google Ads)."),
    (r"\b(META\s*ADS|FACEBOOK\s*ADS|INSTAGRAM\s*ADS)\b", Category.ADVERTISING_MARKETING, 0.98, "Recognized social media advertising (Meta Ads)."),
    (r"\b(LINKEDIN\s*ADS|TWITTER\s*ADS|X\s*ADS)\b", Category.ADVERTISING_MARKETING, 0.98, "Recognized business networking advertising."),
    (r"\b(NAMECHEAP|GODADDY|HOVER|PORKBUN|CLOUDFLARE)\b", Category.ADVERTISING_MARKETING, 0.95, "Recognized domain name registrar and web presence service."),

    # --- Legal & Professional Services (100% Tax Deductible) ---
    (r"\b(UPWORK|FIVERR|TOPTAL|FREELANCER\.COM)\b", Category.PROFESSIONAL_SERVICES, 0.98, "Recognized freelance contractor marketplace / subcontractor payment."),
    (r"\b(LEGALZOOM|ROCKET\s*LAWYER|REGISTERED\s*AGENT)\b", Category.PROFESSIONAL_SERVICES, 0.95, "Recognized corporate legal compliance service."),
    (r"\b(QUICKBOOKS|FRESHBOOKS|XERO|GUSTO|DEEL|RIPPLING)\b", Category.PROFESSIONAL_SERVICES, 0.98, "Recognized business accounting & payroll processing service."),

    # --- Banking & Processing Fees (100% Tax Deductible) ---
    (r"\b(MONTHLY\s*(?:SERVICE|MAINTENANCE)\s*FEE|ACCOUNT\s*FEE)\b", Category.BANKING_FEES, 0.98, "Bank monthly account maintenance fee."),
    (r"\b(WIRE\s*(?:TRANSFER\s*)?FEE|INCOMING\s*WIRE\s*FEE|OUTGOING\s*WIRE\s*FEE)\b", Category.BANKING_FEES, 0.98, "Bank wire transfer processing fee."),
    (r"\b(OVERDRAFT\s*FEE|NSF\s*FEE|ATM\s*(?:SURCHARGE|FEE)|FOREIGN\s*TX\s*FEE)\b", Category.BANKING_FEES, 0.98, "Bank banking or international transaction fee."),
    (r"\b(STRIPE\s*FEE|PAYPAL\s*FEE|MERCHANT\s*DISCOUNT\s*FEE)\b", Category.BANKING_FEES, 0.98, "Merchant gateway transaction processing fee."),

    # --- Utilities & Communications (Business Share) ---
    (r"\b(VERIZON|AT&T|T-MOBILE|COMCAST|XFINITY|SPECTRUM)\b", Category.UTILITIES_INTERNET, 0.90, "Recognized telecommunications and internet provider."),
]

# Ambiguous / Mixed-Use Merchants (MUST go to Needs Review unless specifically tagged)
AMBIGUOUS_RETAILERS: Dict[str, str] = {
    "TARGET": "Mixed personal/office retailer. Could be home groceries or office supplies.",
    "WALMART": "Mixed personal/business department store. Receipts must be audited.",
    "AMAZON": "General marketplace without digital services tag. Verify if business expense.",
    "AMZN MKTP": "Amazon marketplace merchant. Verify whether business supply or personal.",
    "COSTCO": "Warehouse club. Mixed personal groceries and bulk office items.",
    "CVS": "Pharmacy retailer. Typically personal unless emergency office first-aid.",
    "WALGREENS": "Pharmacy retailer. Typically personal unless emergency office first-aid.",
    "DOLLAR TREE": "Discount store. Typically personal unless office cleaning supplies.",
}

# Known Canonical Merchants for Fuzzy Matching (canonical name -> Category)
CANONICAL_MERCHANTS: Dict[str, str] = {
    "ADOBE": Category.SOFTWARE_SAAS,
    "FIGMA": Category.SOFTWARE_SAAS,
    "CANVA": Category.SOFTWARE_SAAS,
    "GITHUB": Category.SOFTWARE_SAAS,
    "GITLAB": Category.SOFTWARE_SAAS,
    "JETBRAINS": Category.SOFTWARE_SAAS,
    "VERCEL": Category.SOFTWARE_SAAS,
    "NETLIFY": Category.SOFTWARE_SAAS,
    "HEROKU": Category.SOFTWARE_SAAS,
    "DIGITALOCEAN": Category.SOFTWARE_SAAS,
    "OPENAI": Category.SOFTWARE_SAAS,
    "ANTHROPIC": Category.SOFTWARE_SAAS,
    "NOTION": Category.SOFTWARE_SAAS,
    "SLACK": Category.SOFTWARE_SAAS,
    "ZOOM": Category.SOFTWARE_SAAS,
    "DROPBOX": Category.SOFTWARE_SAAS,
    "WEWORK": Category.OFFICE_SUPPLIES,
    "STAPLES": Category.OFFICE_SUPPLIES,
    "UBER": Category.TRAVEL_TRANSIT,
    "LYFT": Category.TRAVEL_TRANSIT,
    "AIRBNB": Category.TRAVEL_TRANSIT,
    "MARRIOTT": Category.TRAVEL_TRANSIT,
    "HILTON": Category.TRAVEL_TRANSIT,
    "UPWORK": Category.PROFESSIONAL_SERVICES,
    "FIVERR": Category.PROFESSIONAL_SERVICES,
    "QUICKBOOKS": Category.PROFESSIONAL_SERVICES,
    "LEGALZOOM": Category.PROFESSIONAL_SERVICES,
    "NAMECHEAP": Category.ADVERTISING_MARKETING,
    "GODADDY": Category.ADVERTISING_MARKETING,
}

# Meal & Cafe Keyword Patterns (Subject to 50% IRS deduction limit)
MEAL_PATTERNS = [
    r"\b(STARBUCKS|PEETS\s*COFFEE|BLUE\s*BOTTLE|DUNKIN)\b",
    r"\b(SWEETGREEN|CHIPOTLE|PANERA|SHAKE\s*SHACK)\b",
    r"\b(DOORDASH|UBER\s*EATS|GRUBHUB|POSTMATES|CAVIAR)\b",
    r"\b(CAFE|COFFEE|BAKERY|BISTRO|DINER|PIZZA|GRILL|RESTAURANT|SUSHI|TAQUERIA|DELI)\b",
]
