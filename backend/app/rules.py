"""Rules for the categorizer: plain keyword lists, no AI model.

To teach the app a new merchant, add a keyword to the right list below.
Keywords match whole words/phrases only, so "AWS" will not match "LAWS".
"""

SPENDING_CATEGORIES = [
    "Software",
    "Travel",
    "Meals",
    "Office Supplies",
    "Advertising",
    "Utilities",
]
NOT_SPENDING = "Not Spending"
REFUND = "Refund"
NEEDS_REVIEW = "Needs Review"
ALL_CATEGORIES = SPENDING_CATEGORIES + [NOT_SPENDING, REFUND, NEEDS_REVIEW]

KEYWORDS = {
    "Software": [
        "ADOBE", "FIGMA", "CANVA", "NOTION", "SLACK", "ZOOM", "DROPBOX",
        "GITHUB", "AWS", "AMAZON WEB SERVICES", "GOOGLE WORKSPACE",
        "MICROSOFT 365", "OPENAI", "SKETCH", "FRAMER", "SQUARESPACE",
        "ENVATO", "MAILCHIMP", "FONTSHOP", "LINEAR",
    ],
    "Travel": [
        "UBER", "UBER TRIP", "LYFT", "CAREEM", "AIRLINES", "AIRWAYS",
        "EMIRATES", "QATAR AIRWAYS", "HOTEL", "AIRBNB", "BOOKING.COM",
        "TRAIN", "METRO", "PARKING", "SHELL", "PETROL",
    ],
    "Meals": [
        "UBER EATS", "DOORDASH", "FOODPANDA", "STARBUCKS", "RESTAURANT",
        "CAFE", "COFFEE", "PIZZA", "BURGER", "KFC", "MCDONALDS", "DINER",
    ],
    "Office Supplies": [
        "STAPLES", "OFFICE DEPOT", "PRINTER", "INK", "PAPER", "STATIONERY",
        "WACOM", "APPLE STORE", "IKEA",
    ],
    "Advertising": [
        "GOOGLE ADS", "FACEBOOK ADS", "META ADS", "LINKEDIN ADS",
        "INSTAGRAM ADS", "BEHANCE", "DRIBBBLE PRO",
    ],
    "Utilities": [
        "ELECTRIC", "ELECTRICITY", "INTERNET", "BROADBAND", "WATER BILL",
        "GAS BILL", "VODAFONE", "VERIZON", "COMCAST", "PTCL",
    ],
}

# Names that could be two different things (Amazon sells software AND paper).
# If this is the best match, the row goes to Needs Review.
AMBIGUOUS = ["AMAZON", "AMZN", "PAYPAL", "STRIPE", "SQ", "SQUARE", "WALMART", "TARGET"]

# Moving money around is not spending.
TRANSFER_PHRASES = [
    "TRANSFER TO", "TRANSFER FROM", "INTERNAL TRANSFER", "TO SAVINGS",
    "FROM SAVINGS", "PAYMENT THANK YOU", "AUTOPAY PAYMENT", "CARD PAYMENT",
]

# Words that show money came back from a purchase.
REFUND_WORDS = ["REFUND", "REVERSAL", "REVERSED", "CHARGEBACK"]
