"""Curated merchant → category dictionary.

Confidence: 0.95 for exact dict hit.
mixed_use merchants always trigger Needs Review regardless.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MerchantEntry:
    category_slug: str
    confidence: float = 0.95
    mixed_use: bool = False
    note: str = ""


# Key = normalized merchant name (uppercase, stripped)
MERCHANT_DICT: dict[str, MerchantEntry] = {
    # ── Software & Subscriptions ───────────────────────────────────────────────
    "ADOBE": MerchantEntry("software", note="Adobe Creative Cloud"),
    "ADOBE CREATIVE CLOUD": MerchantEntry("software"),
    "FIGMA": MerchantEntry("software"),
    "GITHUB": MerchantEntry("software"),
    "NOTION": MerchantEntry("software"),
    "SLACK": MerchantEntry("software"),
    "ASANA": MerchantEntry("software"),
    "DROPBOX": MerchantEntry("software"),
    "GOOGLE WORKSPACE": MerchantEntry("software"),
    "GSUITE": MerchantEntry("software"),
    "ZOOM": MerchantEntry("software"),
    "LOOM": MerchantEntry("software"),
    "LINEAR": MerchantEntry("software"),
    "AIRTABLE": MerchantEntry("software"),
    "MONDAY": MerchantEntry("software"),
    "CLICKUP": MerchantEntry("software"),
    "CANVA": MerchantEntry("software"),
    "SKETCH": MerchantEntry("software"),
    "INVISION": MerchantEntry("software"),
    "FRAMER": MerchantEntry("software"),
    "WEBFLOW": MerchantEntry("software"),
    "MAILCHIMP": MerchantEntry("software"),
    "CONVERTKIT": MerchantEntry("software"),
    "HUBSPOT": MerchantEntry("software"),
    "CALENDLY": MerchantEntry("software"),
    "TYPEFORM": MerchantEntry("software"),
    "INTERCOM": MerchantEntry("software"),
    "ZENDESK": MerchantEntry("software"),
    "ANTHROPIC": MerchantEntry("software", note="AI API"),
    "OPENAI": MerchantEntry("software", note="AI API"),
    "VERCEL": MerchantEntry("software"),
    "NETLIFY": MerchantEntry("software"),
    "HEROKU": MerchantEntry("software"),
    "DIGITALOCEAN": MerchantEntry("software"),
    "LINODE": MerchantEntry("software"),
    "CLOUDFLARE": MerchantEntry("software"),
    "GITHUB COPILOT": MerchantEntry("software"),
    "SPOTIFY": MerchantEntry("software", mixed_use=True,
                             note="Personal or business background music"),
    "APPLE": MerchantEntry("software", mixed_use=True, note="Apps or personal devices"),
    "MICROSOFT": MerchantEntry("software"),
    "OFFICE 365": MerchantEntry("software"),
    "QUICKBOOKS": MerchantEntry("software"),
    "FRESHBOOKS": MerchantEntry("software"),
    "WAVE": MerchantEntry("software"),
    "XERO": MerchantEntry("software"),
    # ── Advertising ───────────────────────────────────────────────────────────
    "GOOGLE ADS": MerchantEntry("advertising"),
    "FACEBOOK ADS": MerchantEntry("advertising"),
    "META": MerchantEntry("advertising"),
    "TWITTER ADS": MerchantEntry("advertising"),
    "LINKEDIN ADS": MerchantEntry("advertising"),
    "MAILGUN": MerchantEntry("advertising"),
    "SENDGRID": MerchantEntry("advertising"),
    "FIVERR": MerchantEntry("advertising", mixed_use=True),
    "UPWORK": MerchantEntry("contract_labor"),
    # ── Travel ────────────────────────────────────────────────────────────────
    "UBER": MerchantEntry("travel", mixed_use=True, note="Business or personal"),
    "LYFT": MerchantEntry("travel", mixed_use=True),
    "DELTA AIR": MerchantEntry("travel"),
    "UNITED AIRLINES": MerchantEntry("travel"),
    "AMERICAN AIRLINES": MerchantEntry("travel"),
    "SOUTHWEST AIRLINES": MerchantEntry("travel"),
    "JETBLUE": MerchantEntry("travel"),
    "SPIRIT AIRLINES": MerchantEntry("travel"),
    "FRONTIER AIRLINES": MerchantEntry("travel"),
    "ALASKA AIRLINES": MerchantEntry("travel"),
    "AIRBNB": MerchantEntry("travel", mixed_use=True),
    "MARRIOTT": MerchantEntry("travel"),
    "HILTON": MerchantEntry("travel"),
    "HYATT": MerchantEntry("travel"),
    "IHG": MerchantEntry("travel"),
    "HERTZ": MerchantEntry("travel"),
    "ENTERPRISE": MerchantEntry("travel"),
    "AVIS": MerchantEntry("travel"),
    "BUDGET RENT": MerchantEntry("travel"),
    "EXPEDIA": MerchantEntry("travel", mixed_use=True),
    "BOOKING": MerchantEntry("travel", mixed_use=True),
    # ── Meals ─────────────────────────────────────────────────────────────────
    "STARBUCKS": MerchantEntry("meals"),
    "DOORDASH": MerchantEntry("meals", mixed_use=True),
    "GRUBHUB": MerchantEntry("meals", mixed_use=True),
    "UBER EATS": MerchantEntry("meals", mixed_use=True),
    "INSTACART": MerchantEntry("meals", mixed_use=True),
    "CHIPOTLE": MerchantEntry("meals"),
    "MCDONALD": MerchantEntry("meals"),
    "SUBWAY": MerchantEntry("meals"),
    "PANERA": MerchantEntry("meals"),
    "PEET": MerchantEntry("meals"),
    "DUNKIN": MerchantEntry("meals"),
    # ── Legal & Professional ───────────────────────────────────────────────────
    "DOCUSIGN": MerchantEntry("legal_professional"),
    "HELLOSIGN": MerchantEntry("legal_professional"),
    "LEGALZOOM": MerchantEntry("legal_professional"),
    # ── Utilities ─────────────────────────────────────────────────────────────
    "VERIZON": MerchantEntry("utilities"),
    "AT&T": MerchantEntry("utilities"),
    "T-MOBILE": MerchantEntry("utilities"),
    "COMCAST": MerchantEntry("utilities"),
    "SPECTRUM": MerchantEntry("utilities"),
    "GOOGLE FI": MerchantEntry("utilities"),
    "TWILIO": MerchantEntry("utilities"),
    "ZOOM PHONE": MerchantEntry("utilities"),
    # ── Office / Supplies ──────────────────────────────────────────────────────
    "STAPLES": MerchantEntry("supplies"),
    "OFFICE DEPOT": MerchantEntry("supplies"),
    "OFFICEMAX": MerchantEntry("supplies"),
    "FED EX": MerchantEntry("office_expense"),
    "FEDEX": MerchantEntry("office_expense"),
    "UPS": MerchantEntry("office_expense"),
    "USPS": MerchantEntry("office_expense"),
    # ── Education ─────────────────────────────────────────────────────────────
    "UDEMY": MerchantEntry("education"),
    "SKILLSHARE": MerchantEntry("education"),
    "LINKEDIN LEARNING": MerchantEntry("education"),
    "COURSERA": MerchantEntry("education"),
    "MASTERCLASS": MerchantEntry("education"),
    "PLURALSIGHT": MerchantEntry("education"),
    # ── Payment processors (commissions) ──────────────────────────────────────
    "STRIPE": MerchantEntry("commissions"),
    "SQUARE": MerchantEntry("commissions"),
    "PAYPAL": MerchantEntry("commissions", mixed_use=True, note="Fee or personal?"),
    "VENMO": MerchantEntry("commissions", mixed_use=True),
    "GUMROAD": MerchantEntry("commissions"),
    "SHOPIFY": MerchantEntry("commissions"),
    # ── Rent ──────────────────────────────────────────────────────────────────
    "WEWORK": MerchantEntry("rent_cowork"),
    "REGUS": MerchantEntry("rent_cowork"),
    "INDUSTRIOUS": MerchantEntry("rent_cowork"),
    "COWORKING": MerchantEntry("rent_cowork"),
    # ── Insurance ─────────────────────────────────────────────────────────────
    "HISCOX": MerchantEntry("insurance"),
    "NEXT INSURANCE": MerchantEntry("insurance"),
    "STATE FARM": MerchantEntry("insurance", mixed_use=True),
    # ── Mixed-use (always needs review) ───────────────────────────────────────
    "AMAZON": MerchantEntry("supplies", mixed_use=True,
                            note="Amazon sells both business and personal items"),
    "COSTCO": MerchantEntry("supplies", mixed_use=True),
    "WALMART": MerchantEntry("supplies", mixed_use=True),
    "TARGET": MerchantEntry("supplies", mixed_use=True),
    "BEST BUY": MerchantEntry("equipment", mixed_use=True),
    "B&H": MerchantEntry("equipment", mixed_use=True, note="Photo/video equipment"),
    "ADORAMA": MerchantEntry("equipment", mixed_use=True),
    "ZELLE": MerchantEntry("non_pl", mixed_use=True, note="Personal or business payment?"),
    # ── Income sources ─────────────────────────────────────────────────────────
    "STRIPE TRANSFER": MerchantEntry("client_income"),
    "PAYPAL TRANSFER": MerchantEntry("client_income"),
    "PAYPAL PAYMENT": MerchantEntry("client_income"),
}
