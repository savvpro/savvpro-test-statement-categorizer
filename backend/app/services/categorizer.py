from app.utils.normalizer import normalize
from app.models.transaction import Category

RULES: dict[Category, list[str]] = {
    Category.SOFTWARE: [
        "ADOBE", "FIGMA", "NOTION", "GITHUB", "SLACK", "ZOOM",
        "DROPBOX", "GOOGLE WORKSPACE", "MICROSOFT", "CANVA",
        "INVISION", "SKETCH", "MIRO", "LOOM", "LINEAR",
    ],
    Category.TRAVEL: [
        "UBER", "LYFT", "GRAB", "CAREEM", "AIRLINE", "AIRBNB",
        "BOOKING", "HOTELS", "INDIGO", "EMIRATES", "BRITISH AIRWAYS",
        "TRAIN", "BUS", "TAXI", "PARKING", "TOLL",
    ],
    Category.MEALS: [
        "CAFE", "COFFEE", "STARBUCKS", "RESTAURANT", "SWIGGY",
        "ZOMATO", "DOORDASH", "UBER EATS", "GRUBHUB", "MCDONALDS",
        "SUBWAY", "PIZZA", "FOOD", "DINER", "BAKERY", "BAR",
    ],
    Category.OFFICE: [
        "AMAZON", "STAPLES", "OFFICE DEPOT", "IKEA", "DARAZ",
        "APPLE STORE", "BEST BUY", "PRINTER", "PAPER", "SUPPLIES",
    ],
    Category.UTILITIES: [
        "ELECTRICITY", "INTERNET", "WIFI", "PTCL", "JAZZ",
        "UFONE", "ZONG", "TELENOR", "PHONE", "MOBILE", "UTILITY",
    ],
    Category.ADVERTISING: [
        "FACEBOOK ADS", "GOOGLE ADS", "META ADS", "TWITTER ADS",
        "LINKEDIN ADS", "MAILCHIMP", "HUBSPOT", "INSTAGRAM",
    ],
    Category.TRANSFER: [
        "TRANSFER", "PAYMENT TO", "SENT TO", "WITHDRAWAL",
        "SAVINGS", "JAZZ CASH", "EASYPAISA", "PAYONEER",
    ],
    Category.FREELANCE: [
        "UPWORK", "FIVERR", "PAYPAL", "WISE", "TOPTAL",
        "FREELANCER", "DEPOSIT", "CLIENT PAYMENT",
    ],
}


def categorize(description: str, amount: float) -> tuple[Category, str]:
    """
    Returns (category, confidence).
    confidence is 'high' or 'low'.
    """

    # Refund: negative amount
    if amount < 0:
        return Category.REFUND, "high"

    normalized = normalize(description)

    for category, keywords in RULES.items():
        for keyword in keywords:
            if keyword in normalized:
                return category, "high"

    # Partial / fuzzy fallback — low confidence
    for category, keywords in RULES.items():
        for keyword in keywords:
            words = keyword.split()
            if any(word in normalized for word in words if len(word) > 3):
                return category, "low"

    return Category.NEEDS_REVIEW, "low"