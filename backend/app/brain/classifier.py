import re
from dataclasses import dataclass
from decimal import Decimal

from .normalizer import normalize

NEEDS_REVIEW = "Needs Review"

SPEND_RULES = {
    "Software": ["ADOBE", "GITHUB", "MICROSOFT", "FIGMA", "JETBRAINS", "SLACK", "ZOOM",
                 "NOTION", "DROPBOX", "OPENAI", "CANVA", "NAMECHEAP", "GODADDY",
                 "DIGITALOCEAN", "AMAZON WEB SERVICES", "GOOGLE WORKSPACE"],
    "Travel": ["UBER TRIP", "UBER", "LYFT", "TAXI", "AIRLINES", "AIRWAYS", "QANTAS",
               "HOTEL", "AIRBNB", "BOOKING COM", "PARKING", "TOLL"],
    "Meals": ["UBER EATS", "DOORDASH", "MENULOG", "STARBUCKS", "MCDONALD", "KFC",
              "RESTAURANT", "PIZZA"],
    "Office": ["STAPLES", "OFFICE DEPOT", "OFFICEWORKS"],
    "Utilities": ["ELECTRIC", "INTERNET", "TELSTRA", "OPTUS", "VODAFONE",
                  "WATER BILL", "GAS BILL", "ORIGIN ENERGY"],
    # Merchants that sell everything: guessing would be wrong.
    NEEDS_REVIEW: ["AMAZON", "WALMART", "TARGET", "PAYPAL", "SQUARE", "EBAY",
                   "COSTCO", "KMART", "WOOLWORTHS", "COLES"],
}
TRANSFER_WORDS = ["TRANSFER TO", "TRANSFER FROM", "INTERNAL TRANSFER", "PAYMENT THANK YOU"]
REFUND_WORDS = ["REFUND", "REVERSAL", "RETURN"]
INCOME_WORDS = ["CLIENT PAYMENT", "INVOICE", "PAYMENT FROM"]


@dataclass(frozen=True)
class Result:
    category: str
    reason: str

    @property
    def needs_review(self) -> bool:
        return self.category == NEEDS_REVIEW


def _has(text: str, keyword: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(_has(text, k) for k in keywords)


def _match(text: str):
    """Longest keyword wins ('UBER EATS' beats 'UBER'). Tie across categories = conflict."""
    hits = [(len(kw), cat, kw)
            for cat, kws in SPEND_RULES.items() for kw in kws if _has(text, kw)]
    if not hits:
        return None, None
    top = max(h[0] for h in hits)
    best = [h for h in hits if h[0] == top]
    if len({h[1] for h in best}) > 1:
        return "CONFLICT", None
    return best[0][1], best[0][2]


def classify(description: str, amount: Decimal) -> Result:
    text = normalize(description)
    if not text:
        return Result(NEEDS_REVIEW, "empty description")
    if _has_any(text, TRANSFER_WORDS):
        return Result("Transfer", "internal transfer, not spending")
    if amount == 0:
        return Result(NEEDS_REVIEW, "zero amount")
    if amount > 0:  # money coming in
        if _has_any(text, REFUND_WORDS):
            return Result("Refund", "money back, not income")
        if _has_any(text, INCOME_WORDS):
            return Result("Income", "matched income keyword")
        return Result(NEEDS_REVIEW, "unknown incoming money")
    category, keyword = _match(text)  # money going out
    if category is None:
        return Result(NEEDS_REVIEW, "unknown merchant")
    if category == "CONFLICT":
        return Result(NEEDS_REVIEW, "conflicting rules")
    if category == NEEDS_REVIEW:
        return Result(NEEDS_REVIEW, "ambiguous merchant")
    return Result(category, f"matched '{keyword}'")
