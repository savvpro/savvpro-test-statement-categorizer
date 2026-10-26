"""Rule-based categorizer (the "brain"). No AI model is used for decisions.

Sign convention comes from the parser: amount > 0 is money OUT, amount < 0 is money IN.
"""
import re

from app.models import CategorizedTransaction, Transaction

REVIEW_THRESHOLD = 0.75
NEEDS_REVIEW = "Needs Review"

SPEND_RULES: dict[str, list[str]] = {
    "Software": [
        "ADOBE", "GITHUB", "FIGMA", "NOTION", "SLACK", "OPENAI", "GSUITE",
        "GOOGLE WORKSPACE", "ZOOM", "DROPBOX", "HETZNER", "NAMECHEAP",
        "DIGITALOCEAN", "AWS",
    ],
    "Travel": ["UBER", "LYFT", "CAREEM", "SHELL OIL", "BOOKING.COM", "AIRBNB", "AIRLINES"],
    "Meals": ["UBER EATS", "DOORDASH", "FOODPANDA", "STARBUCKS", "COFFEE", "MCDONALDS", "KFC", "RESTAURANT"],
    "Office": ["COWORKING", "STAPLES", "OFFICE DEPOT"],
    "Education": ["COURSERA", "UDEMY"],
    "Contractors": ["FIVERR", "UPWORK"],
    "Fees & Interest": ["FOREIGN TRANSACTION FEE", "INTEREST CHARGE", "LATE FEE", "ANNUAL FEE"],
}

# Merchants where the same name can mean different things: never guess.
AMBIGUOUS: dict[str, str] = {
    "AMZN MKTP": "Marketplace purchase: could be office supplies or personal",
    "AMAZON": "Marketplace purchase: could be office supplies or personal",
    "APPLE.COM/BILL": "Apple billing: could be a subscription or hardware",
    "WALMART": "General store: mixed purchases, needs a human decision",
}

TRANSFER_WORDS = ["TRANSFER TO", "TRANSFER FROM", "OWN ACCOUNT"]
PAYMENT_WORDS = ["PAYMENT THANK YOU", "AUTOPAY", "PAYMENT RECEIVED"]
REFUND_WORDS = ["REFUND", "REVERSAL", "CHARGEBACK"]
CASHBACK_WORDS = ["CASHBACK", "REWARD"]


def normalize(desc: str) -> str:
    text = re.sub(r"[*#]", " ", desc.upper())
    return re.sub(r"\s+", " ", text).strip()


def merchant_key(desc: str) -> str:
    """Stable key used to remember user corrections (digits and refs removed)."""
    tokens = [t for t in normalize(desc).split() if not any(c.isdigit() for c in t)]
    return " ".join(tokens[:2])


def _find(keyword: str, text: str) -> bool:
    # whole-word start, and no letter right after: ZOOM must not match ZOOMER
    return re.search(rf"(?<![A-Z0-9]){re.escape(keyword)}(?![A-Z])", text) is not None


def _result(txn, category, confidence, reason, rule=None) -> CategorizedTransaction:
    return CategorizedTransaction(
        transaction=txn,
        category=category,
        confidence=confidence,
        reason=reason,
        needs_review=category == NEEDS_REVIEW or confidence < REVIEW_THRESHOLD,
        matched_rule=rule,
    )


def categorize(txn: Transaction, memory: dict[str, str] | None = None) -> CategorizedTransaction:
    if not txn.is_valid:
        detail = "; ".join(txn.errors) or "missing amount"
        return _result(txn, NEEDS_REVIEW, 0.0, f"Row could not be read: {detail}")

    text = normalize(txn.description)

    # Money direction and explicit financial events take precedence
    # over user-learned merchant categories.
    if txn.amount < 0:  # money IN
        for w in REFUND_WORDS:
            if _find(w, text):
                return _result(txn, "Refund", 0.9, "Money back, not income", w)
        for w in PAYMENT_WORDS:
            if _find(w, text):
                return _result(txn, "Transfer", 0.95, "Card payment, not spending", w)
        for w in CASHBACK_WORDS:
            if _find(w, text):
                return _result(txn, "Credit", 0.9, "Cashback or reward credit", w)
        return _result(txn, NEEDS_REVIEW, 0.3, "Unknown credit: could be refund or something else")

    # An outgoing row labeled as a refund/reversal is suspicious.
    # Do not silently count it as an ordinary business expense.
    if any(_find(w, text) for w in REFUND_WORDS):
        return _result(
            txn, NEEDS_REVIEW, 0.2,
            "Outgoing refund/reversal requires manual verification"
        )

    for w in TRANSFER_WORDS:  # money OUT
        if _find(w, text):
            return _result(txn, "Transfer", 0.95, "Transfer between accounts, not spending", w)

    key = merchant_key(txn.description)
    if memory and key in memory:
        return _result(
            txn, memory[key], 1.0,
            "Learned from your earlier correction", "memory"
        )

    hits = []
    for cat, kws in SPEND_RULES.items():
        for kw in kws:
            if _find(kw, text):
                hits.append((len(kw), cat, kw, 0.9, f"Matched '{kw}'"))
    for kw, note in AMBIGUOUS.items():
        if _find(kw, text):
            hits.append((len(kw), NEEDS_REVIEW, kw, 0.4, note))

    if not hits:
        return _result(txn, NEEDS_REVIEW, 0.2, "No rule matched")

    best = max(h[0] for h in hits)  # most specific (longest) keyword wins
    top = [h for h in hits if h[0] == best]
    if len({h[1] for h in top}) > 1:
        names = ", ".join(sorted({h[1] for h in top}))
        return _result(txn, NEEDS_REVIEW, 0.5, f"Ambiguous: matches {names}")
    _, cat, kw, conf, reason = top[0]
    return _result(txn, cat, conf, reason, kw)
