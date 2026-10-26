"""Static knowledge for the brain: categories, merchant keywords, regexes.

Use case: a freelance software developer's business credit card / bank statement.
"""
import re

REVIEW = "Needs Review"
NOT_SPENDING = "Not Spending"
INCOME = "Income"

CATEGORIES = [
    "Software", "Hosting & Cloud", "Travel", "Meals", "Office & Equipment",
    "Advertising", "Professional Services", "Utilities & Internet", "Education",
    "Bank Fees & Interest", NOT_SPENDING, INCOME, REVIEW,
]

MERCHANTS: dict[str, str] = {
    # Software
    "ADOBE": "Software", "FIGMA": "Software", "GITHUB": "Software", "NOTION": "Software",
    "SLACK": "Software", "ZOOM": "Software", "JETBRAINS": "Software", "OPENAI": "Software",
    "DROPBOX": "Software", "MICROSOFT": "Software", "CANVA": "Software", "1PASSWORD": "Software",
    "GOOGLE WORKSPACE": "Software",
    # Hosting & Cloud
    "AWS": "Hosting & Cloud", "AMAZON WEB SERVICES": "Hosting & Cloud",
    "DIGITALOCEAN": "Hosting & Cloud", "VERCEL": "Hosting & Cloud", "NETLIFY": "Hosting & Cloud",
    "HEROKU": "Hosting & Cloud", "CLOUDFLARE": "Hosting & Cloud", "NAMECHEAP": "Hosting & Cloud",
    "GODADDY": "Hosting & Cloud",
    # Travel
    "UBER": "Travel", "LYFT": "Travel", "DELTA AIR": "Travel", "UNITED AIRLINES": "Travel",
    "AIRBNB": "Travel", "MARRIOTT": "Travel", "HILTON": "Travel",
    # Meals
    "UBER EATS": "Meals", "STARBUCKS": "Meals", "DOORDASH": "Meals", "CHIPOTLE": "Meals",
    "MCDONALDS": "Meals", "PANERA": "Meals",
    # Office & Equipment
    "STAPLES": "Office & Equipment", "BEST BUY": "Office & Equipment", "APPLE STORE": "Office & Equipment",
    # Advertising
    "GOOGLE ADS": "Advertising", "FACEBK": "Advertising", "META ADS": "Advertising",
    "LINKEDIN ADS": "Advertising",
    # Professional services
    "QUICKBOOKS": "Professional Services", "INTUIT": "Professional Services",
    "LEGALZOOM": "Professional Services", "UPWORK": "Professional Services",
    # Utilities
    "COMCAST": "Utilities & Internet", "VERIZON": "Utilities & Internet", "AT&T": "Utilities & Internet",
    "T-MOBILE": "Utilities & Internet", "SPECTRUM": "Utilities & Internet",
    # Education
    "UDEMY": "Education", "COURSERA": "Education", "OREILLY": "Education",
}

# Merchants that can be anything. Never guess: send to review.
AMBIGUOUS = ["AMZN", "AMAZON", "PAYPAL", "SQ", "SQUARE", "WALMART", "COSTCO", "TARGET",
             "VENMO", "CASH APP", "ZELLE", "ATM", "CHECK"]

TRANSFER_RE = re.compile(r"\b(TRANSFER|XFER)\b")
PAYMENT_RE = re.compile(r"\b(AUTOPAY|PAYMENT THANK YOU|ONLINE PAYMENT|CARD PAYMENT|PAYMENT RECEIVED)\b")
FEE_RE = re.compile(r"\b(ANNUAL FEE|LATE FEE|FOREIGN TRANSACTION FEE|FX FEE|SERVICE FEE|OVERDRAFT|INTEREST CHARGE|PURCHASE INTEREST)\b")
REFUND_RE = re.compile(r"\b(REFUND|RETURN|REVERSAL|CHARGEBACK)\b")
INCOME_RE = re.compile(r"\b(DIRECT DEP\w*|DEPOSIT|PAYOUT|INVOICE|PAYMENT FROM)\b")


def keyword_re(key: str) -> re.Pattern:
    return re.compile(r"(?<![A-Z0-9])" + re.escape(key) + r"(?![A-Z0-9])")
