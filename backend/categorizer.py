"""Deterministic, rule-based transaction categorizer.

No AI model is involved. Every decision comes from the explicit rules below and
is returned together with a human-readable reason.

Sign convention (documented in DESIGN.md):
    positive amount = money spent / charged (or money received for income rows)
    negative amount = credit / money back (refund, reversal, card payment)

The sign is only used as a *safety check*: when the wording and the sign
disagree, the row is sent to review instead of being guessed.
"""

import re

NEEDS_REVIEW = "Needs Review"

CATEGORIES = [
    "Software",
    "Travel",
    "Office Supplies",
    "Advertising",
    "Phone & Internet",
    "Bank Fees",
    "Education & Training",
    "Groceries",
    "Meals",
    "Income",
    "Transfer",
    NEEDS_REVIEW,
]

# Each keyword is a regular expression matched on word boundaries, so "train"
# no longer matches "training" and "uber" does not match "uber eats".
EXPENSE_RULES = [
    ("Software", [
        r"adobe", r"microsoft 365", r"office 365", r"github", r"figma", r"dropbox",
        r"canva", r"notion", r"slack", r"zoom", r"google workspace", r"envato",
        r"shutterstock", r"fontspring", r"squarespace", r"webflow",
    ]),
    ("Travel", [
        r"uber(?! ?eats)", r"lyft", r"taxi", r"airline", r"airways", r"flight",
        r"hotel", r"airbnb", r"train", r"parking", r"toll",
    ]),
    ("Office Supplies", [r"office depot", r"staples", r"office supplies", r"stationery"]),
    ("Advertising", [r"facebook ads", r"meta ads", r"google ads", r"advertising", r"linkedin ads"]),
    ("Phone & Internet", [r"at&t", r"verizon", r"comcast", r"t-mobile", r"internet", r"phone bill"]),
    ("Bank Fees", [
        r"bank fee", r"service charge", r"monthly fee", r"transfer fee", r"wire fee",
        r"overdraft", r"annual fee", r"late fee",
    ]),
    ("Education & Training", [r"udemy", r"coursera", r"skillshare", r"training course", r"workshop"]),
    ("Groceries", [r"whole foods", r"grocery", r"supermarket"]),
    ("Meals", [
        r"restaurant", r"doordash", r"grubhub", r"coffee shop", r"uber ?eats",
        r"starbucks",
    ]),
]

TRANSFER_PATTERNS = [
    r"transfer to savings", r"transfer from savings", r"transfer between accounts",
    r"internal transfer", r"account transfer", r"credit card payment",
    r"payment thank you", r"autopay", r"online payment", r"card payment",
]

INCOME_PATTERNS = [
    r"client payment", r"freelance payment", r"invoice payment", r"customer payment",
    r"business income", r"stripe payout", r"paypal payout",
]

REFUND_PATTERNS = [r"refund", r"chargeback", r"reversal", r"returned payment"]


def _compile(patterns):
    return [re.compile(rf"\b(?:{p})\b") for p in patterns]


_EXPENSE = [(cat, _compile(pats)) for cat, pats in EXPENSE_RULES]
_TRANSFER = _compile(TRANSFER_PATTERNS)
_INCOME = _compile(INCOME_PATTERNS)
_REFUND = _compile(REFUND_PATTERNS)


def parse_amount(value):
    """Convert common currency strings into a signed number.

    Handles "$1,234.50", "(25.00)", "-$10", "$-10", "25.00 CR" (credit => negative)
    and "25.00 DR" (debit => positive).
    """
    text = str(value).strip().upper().replace("$", "").replace(",", "").replace(" ", "")
    negative = False
    if text.endswith("CR"):
        negative, text = True, text[:-2]
    elif text.endswith("DR"):
        text = text[:-2]
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1]
    number = float(text)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError("Amount is not a finite number.")
    if negative:
        number = -abs(number)
    return round(number, 2)


def _any(patterns, text):
    return any(p.search(text) for p in patterns)


def _expense_categories(text):
    return [cat for cat, pats in _EXPENSE if _any(pats, text)]


def _review(reason):
    return {"category": NEEDS_REVIEW, "kind": "review", "reason": reason}


def categorize_transaction(description, amount):
    """Return {"category", "kind", "reason"}. Unsure rows go to Needs Review."""
    text = re.sub(r"\s+", " ", str(description).strip().lower())
    amount = parse_amount(amount)

    if not text:
        return _review("Transaction description is missing.")
    if amount == 0:
        return _review("Amount is zero; check this row manually.")

    categories = _expense_categories(text)

    if _any(_TRANSFER, text):
        return {
            "category": "Transfer",
            "kind": "transfer",
            "reason": "Internal transfer or card payment; excluded from spending.",
        }

    if _any(_REFUND, text):
        if amount > 0:
            return _review("Refund wording but a positive (charge) amount; please confirm.")
        if len(categories) == 1:
            return {
                "category": categories[0],
                "kind": "refund",
                "reason": "Refund matched to a known merchant category; reduces that expense.",
            }
        if len(categories) > 1:
            return _review("Refund matches several categories: " + ", ".join(categories) + ".")
        return _review("Refund detected, but its original category is unknown.")

    if _any(_INCOME, text):
        if categories:
            return _review("Looks like income but also matches an expense rule.")
        if amount < 0:
            return _review("Income wording but a negative amount; please confirm.")
        return {
            "category": "Income",
            "kind": "income",
            "reason": "Matched a known business income description.",
        }

    if len(categories) > 1:
        return _review("Matches several categories: " + ", ".join(categories) + ".")

    if len(categories) == 1:
        if amount < 0:
            return _review("Negative amount without refund wording; is this a refund or credit?")
        return {
            "category": categories[0],
            "kind": "expense",
            "reason": f"Matched a configured merchant rule ({categories[0]}).",
        }

    return _review("No reliable merchant rule matched this transaction.")
