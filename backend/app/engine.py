"""Deterministic rules only. Uncertainty is a first-class result, never a guessed score."""

import re
from dataclasses import dataclass

EXPENSE_CATEGORIES = ("Software", "Travel", "Marketing", "Fees", "Office", "Meals", "Other")
CATEGORIES = (*EXPENSE_CATEGORIES, "Client income", "Transfer", "Personal", "Excluded")

# Match word boundaries, so UBER cannot accidentally match SUPERUBER.
MERCHANT_RULES = (
    (
        "software",
        "Software",
        r"\b(?:ADOBE|FIGMA|GITHUB|NOTION|CANVA|MICROSOFT 365|"
        r"GOOGLE WORKSPACE|AMAZON WEB SERVICES|DIGITALOCEAN|VERCEL)\b",
    ),
    ("travel", "Travel", r"\b(?:UBER TRIP|UBER RIDES|LYFT RIDE|TRAINLINE)\b"),
    ("marketing", "Marketing", r"\b(?:GOOGLE ADS|META ADS|FACEBOOK ADS|LINKEDIN ADS)\b"),
    ("fees", "Fees", r"\b(?:STRIPE PROCESSING FEE|BANK FEE|MONTHLY SERVICE FEE|WIRE FEE)\b"),
    ("office", "Office", r"\b(?:STAPLES|OFFICE DEPOT)\b"),
)
TRANSFER = re.compile(
    r"\b(?:TRANSFER (?:TO|FROM) (?:SAVINGS|CHECKING|OWN ACCOUNT)|"
    r"CREDIT CARD PAYMENT|PAYMENT THANK YOU|INTERNAL TRANSFER)\b"
)


@dataclass(frozen=True)
class Decision:
    category: str | None
    kind: str
    status: str
    reason: str
    rule_id: str


def classify(description: str, amount_cents: int) -> Decision:
    normalized = re.sub(r"[^A-Z0-9]+", " ", description.upper()).strip()
    kind = "expense" if amount_cents < 0 else "credit"

    def review(reason: str, rule: str, review_kind: str = kind) -> Decision:
        return Decision(None, review_kind, "needs_review", reason, rule)

    is_transfer = bool(TRANSFER.search(normalized))
    is_refund = bool(re.search(r"\b(?:REFUND|REVERSAL)\b", normalized))
    is_income = bool(re.search(r"\b(?:CLIENT PAYMENT|INVOICE PAYMENT)\b", normalized))
    # Payment processors and broad transfer labels don't establish economic purpose.
    if (is_income and re.search(r"\bTRANSFER\b", normalized)) or sum(
        [is_transfer, is_refund, is_income]
    ) > 1:
        return review(
            "Conflicting transaction signals. Confirm what this payment represents.",
            "conflicting_signals",
        )
    if is_transfer:
        return Decision(
            "Transfer",
            "transfer",
            "categorized",
            "Recognized an internal transfer or card payment; excluded from expenses.",
            "internal_transfer",
        )
    if is_refund and amount_cents < 0:
        return review(
            "Refund wording conflicts with an outgoing amount. Check the statement.",
            "refund_sign_conflict",
        )
    if is_income and amount_cents > 0:
        return Decision(
            "Client income",
            "income",
            "categorized",
            "Incoming payment explicitly labeled as a client or invoice payment.",
            "client_payment",
        )
    matches = [
        (rule, category)
        for rule, category, pattern in MERCHANT_RULES
        if re.search(pattern, normalized)
    ]
    if len(matches) > 1:
        return review(
            "More than one category matched. A person should choose the right one.",
            "conflicting_merchants",
            "refund" if is_refund else kind,
        )
    if amount_cents > 0 and not is_refund:
        return review(
            "An incoming amount is not necessarily income. Confirm its purpose.", "unknown_credit"
        )
    if matches:
        rule, category = matches[0]
        return Decision(
            category,
            "refund" if is_refund else "expense",
            "categorized",
            f"Matched a known {category.lower()} merchant"
            + (
                "; this refund reduces that category's expenses."
                if is_refund
                else " for a freelance design business. Check its business purpose."
            ),
            f"merchant_{rule}",
        )
    return review(
        "No reliable rule matched. Choose a category after checking its purpose.",
        "unknown_merchant",
        "refund" if is_refund else kind,
    )
