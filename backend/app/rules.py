"""The knowledge base of the categorizer: plain data, no logic.

Each rule maps keywords (matched as whole words in the cleaned description)
to a category with a confidence. When several rules match, the highest
confidence wins, then the longest keyword (so UBER EATS beats UBER).
Low-confidence rules are deliberate: they name a *suggestion* for merchants
that are ambiguous (Amazon, PayPal...) so the user is asked instead of guessed at.
"""

from dataclasses import dataclass

SOFTWARE = "Software & Subscriptions"
TRAVEL = "Travel"
MEALS = "Meals & Entertainment"
OFFICE = "Office & Equipment"
ADVERTISING = "Advertising & Marketing"
PROFESSIONAL = "Professional Services"
FEES = "Bank & Platform Fees"
UTILITIES = "Internet & Phone"
EDUCATION = "Education & Training"
PERSONAL = "Personal"
INCOME = "Income"
TRANSFER = "Transfer"
REVIEW = "Needs Review"

EXPENSE_CATEGORIES = [SOFTWARE, TRAVEL, MEALS, OFFICE, ADVERTISING, PROFESSIONAL, FEES, UTILITIES, EDUCATION]
ALL_CATEGORIES = EXPENSE_CATEGORIES + [PERSONAL, INCOME, TRANSFER]

CONFIDENCE_THRESHOLD = 0.7
LARGE_EXPENSE = 5000
LARGE_MEAL = 300


@dataclass(frozen=True)
class Rule:
    keywords: tuple[str, ...]
    category: str
    confidence: float
    direction: str | None = None  # "in", "out" or None for both
    note: str = ""


def _rule(category, confidence, *keywords, direction=None, note=""):
    return Rule(tuple(keywords), category, confidence, direction, note)


RULES: list[Rule] = [
    # Money that is not spending.
    _rule(TRANSFER, 0.98, "TRANSFER TO SAVINGS", "TRANSFER FROM SAVINGS", "INTERNAL TRANSFER",
          "PAYMENT THANK YOU", "AUTOPAY PAYMENT", "CREDIT CARD PAYMENT", "ONLINE PAYMENT THANK YOU",
          note="Moving money between your own accounts is not spending or income"),
    _rule(TRANSFER, 0.5, "TRANSFER", "XFER", note="Generic transfer: could be a client paying you or your own money"),
    # Income (only when money comes in).
    _rule(INCOME, 0.92, "UPWORK", "FIVERR", "PAYONEER", "STRIPE PAYOUT", "STRIPE TRANSFER", "WISE PAYOUT",
          "INVOICE", "CLIENT PAYMENT", direction="in", note="Client or platform payout"),
    # Fees.
    _rule(FEES, 0.96, "FOREIGN TRANSACTION FEE", "FOREIGN TRANS FEE", "FX FEE", "CURRENCY CONVERSION",
          "INTL TRANSACTION FEE", "MONTHLY SERVICE FEE", "ANNUAL FEE", "WIRE FEE", "OVERDRAFT FEE",
          "LATE FEE", "INTEREST CHARGE", direction="out"),
    _rule(FEES, 0.9, "UPWORK FEE", "FIVERR FEE", "PAYONEER FEE", "PAYPAL FEE", "STRIPE FEE", direction="out"),
    # Software & subscriptions.
    _rule(SOFTWARE, 0.95, "ADOBE", "FIGMA", "CANVA", "GITHUB", "NOTION", "SLACK", "ZOOM", "DROPBOX",
          "GOOGLE WORKSPACE", "GSUITE", "MICROSOFT 365", "OFFICE 365", "OPENAI", "ANTHROPIC", "JETBRAINS",
          "DIGITALOCEAN", "HEROKU", "VERCEL", "NETLIFY", "NAMECHEAP", "GODADDY", "CLOUDFLARE", "AWS",
          "AMAZON WEB SERVICES", "SQUARESPACE", "WIX", "MAILCHIMP", "FRESHBOOKS", "QUICKBOOKS", "XERO",
          "ENVATO", "SHUTTERSTOCK", "LASTPASS", "1PASSWORD"),
    # Travel.
    _rule(TRAVEL, 0.93, "UBER", "LYFT", "CAREEM", "BOLT", "AIRLINES", "AIRWAYS", "AIR CANADA",
          "DELTA AIR", "RYANAIR", "EMIRATES", "QATAR AIRWAYS", "SOUTHWEST", "AIRBNB", "BOOKING COM",
          "EXPEDIA", "HOTEL", "MARRIOTT", "HILTON", "HYATT", "AMTRAK", "TRAIN", "METRO TRANSIT", "PARKING",
          "TOLL", "HERTZ", "AVIS", "ENTERPRISE RENT"),
    _rule(MEALS, 0.95, "UBER EATS", "DOORDASH", "GRUBHUB", "DELIVEROO", "FOODPANDA", "STARBUCKS", "MCDONALDS",
          "SUBWAY", "KFC", direction="out", note="Business meals are usually only partly deductible"),
    _rule(MEALS, 0.6, "RESTAURANT", "COFFEE", "CAFE", "BISTRO", "PIZZA", "DINER", "GRILL", "BAKERY",
          direction="out", note="Looks like food, but a business meal or a personal one?"),
    # Office, advertising, services, utilities, education.
    _rule(OFFICE, 0.9, "STAPLES", "OFFICE DEPOT", "APPLE STORE", "BEST BUY", "WACOM", "LOGITECH", "IKEA",
          "COWORKING", "WEWORK", "REGUS", "USPS", "FEDEX", "UPS STORE", "DHL", direction="out"),
    _rule(ADVERTISING, 0.93, "FACEBK", "FACEBOOK ADS", "META ADS", "GOOGLE ADS", "LINKEDIN ADS", "TWITTER ADS",
          "TIKTOK ADS", "MOO PRINT", "VISTAPRINT", direction="out"),
    _rule(PROFESSIONAL, 0.9, "ACCOUNTANT", "ACCOUNTING", "LEGAL", "LAW OFFICE", "ATTORNEY", "NOTARY",
          "BOOKKEEPING", "TAX PREP", "TURBOTAX", "H R BLOCK", direction="out"),
    _rule(UTILITIES, 0.9, "VERIZON", "AT T", "COMCAST", "XFINITY", "VODAFONE", "JAZZ", "ZONG", "PTCL",
          "STORM FIBER", "T MOBILE", "SPECTRUM", "INTERNET", "MOBILE BILL", direction="out"),
    _rule(EDUCATION, 0.9, "UDEMY", "COURSERA", "SKILLSHARE", "DOMESTIKA", "LINKEDIN LEARNING", "MASTERCLASS",
          "O REILLY", direction="out"),
    # Clearly personal: never a business deduction.
    _rule(PERSONAL, 0.92, "NETFLIX", "SPOTIFY", "DISNEY PLUS", "HULU", "HBO", "APPLE MUSIC", "STEAM GAMES",
          "PLAYSTATION", "NINTENDO", "GROCERY", "SUPERMARKET", "WHOLE FOODS", "TRADER JOE", "ALDI", "KROGER",
          "PHARMACY", "CVS", "WALGREENS", "GYM", "FITNESS", "SALON", "BARBER", "CINEMA", "AMC THEATRES",
          "ZARA", "H M", "NIKE", direction="out"),
    # Ambiguous merchants: suggest, but always ask.
    _rule(OFFICE, 0.45, "AMAZON", "AMZN", "WALMART", "TARGET", "COSTCO", "EBAY", direction="out",
          note="Could be business supplies or personal shopping"),
    _rule(SOFTWARE, 0.4, "PAYPAL", "APPLE COM BILL", "GOOGLE PLAY", direction="out",
          note="Payment processor: the real merchant is hidden"),
    _rule(PERSONAL, 0.35, "ATM", "CASH WITHDRAWAL", direction="out", note="Cash use cannot be classified from the statement"),
]
