"""The brain: ordered, explainable rules, with conservative abstention.

No network calls, AI models, learned weights, or external categorization APIs.
The assumption is a dedicated business account belonging to a freelance designer.
"""

import re
import unicodedata
from dataclasses import dataclass

from .domain import Category as C
from .domain import Decision, Kind, ParsedTransaction


def normalize(description: str) -> str:
    """Normalize whitespace/punctuation, but preserve digits for duplicate fingerprints."""
    text = unicodedata.normalize("NFKC", description).upper()
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


@dataclass(frozen=True)
class MerchantRule:
    id: str
    pattern: str
    category: C
    strength: float
    explanation: str
    review: bool = False


# Boundary-aware specific patterns prevent SUBWAY or ADOBESCAM substring mistakes.
# Broad marketplaces, payment processors, and generic Apple purchases are deliberately absent.
MERCHANT_RULES = (
    MerchantRule(
        "software.adobe",
        r"^(?:ADOBE (?:CREATIVE CLOUD|CC)|ADOBE)\b",
        C.SOFTWARE,
        0.96,
        "Adobe software subscription on a dedicated business account.",
    ),
    MerchantRule("software.figma", r"^FIGMA\b", C.SOFTWARE, 0.96, "Figma design software."),
    MerchantRule("software.github", r"^GITHUB\b", C.SOFTWARE, 0.96, "GitHub developer subscription."),
    MerchantRule("software.notion", r"^NOTION\b", C.SOFTWARE, 0.94, "Notion productivity software."),
    MerchantRule("software.dropbox", r"^DROPBOX\b", C.SOFTWARE, 0.94, "Dropbox cloud storage."),
    MerchantRule("software.canva", r"^CANVA\b", C.SOFTWARE, 0.94, "Canva design software."),
    MerchantRule(
        "travel.uber", r"^UBER (?:TRIP|RIDES?)\b", C.TRAVEL, 0.94, "Uber ride; business-account assumption applies."
    ),
    MerchantRule(
        "travel.lyft", r"^LYFT (?:RIDE|TRIP)\b", C.TRAVEL, 0.94, "Lyft ride; business-account assumption applies."
    ),
    MerchantRule(
        "meals.delivery",
        r"^(?:UBER EATS|DOORDASH)\b",
        C.MEALS,
        0.65,
        "Food delivery needs a business-purpose check; no deduction rate is inferred.",
        True,
    ),
    MerchantRule(
        "office.staples",
        r"^STAPLES\b",
        C.OFFICE,
        0.70,
        "Mixed-use retailer: check the receipt and business purpose.",
        True,
    ),
    MerchantRule("marketing.google", r"^GOOGLE ADS\b", C.MARKETING, 0.95, "Explicit Google Ads advertising charge."),
    MerchantRule("marketing.meta", r"^META ADS\b", C.MARKETING, 0.95, "Explicit Meta Ads advertising charge."),
    MerchantRule(
        "fees.account",
        r"^(?:MONTHLY (?:ACCOUNT|SERVICE) FEE|BANK SERVICE FEE|WIRE TRANSFER FEE|FOREIGN TRANSACTION FEE)\b",
        C.FEES,
        0.98,
        "Explicit bank service fee.",
    ),
)

TRANSFER = re.compile(
    r"^(?:TRANSFER (?:TO|FROM) (?:SAVINGS|CHECKING|CURRENT ACCOUNT|OWN ACCOUNT)\b|INTERNAL TRANSFER\b|CREDIT CARD (?:PAYMENT|AUTOPAY)\b|PAYMENT (?:THANK YOU|RECEIVED THANK YOU)\b)"
)
AMBIGUOUS = re.compile(r"\b(?:CHARGEBACK|REVERSAL|DISPUTE|CASHBACK|CASH BACK|REWARD|CASH WITHDRAWAL|ATM)\b")
REFUND = re.compile(r"\b(?:REFUND|REFUNDED|RETURN|RETURNED)\b")


def categorize(tx: ParsedTransaction) -> Decision:
    """Structural rules outrank merchant matching. Unknown credits are never income by default."""
    text = normalize(tx.description)
    if tx.amount_minor == 0:
        return Decision(C.REVIEW, Kind.UNKNOWN, 0, "review.zero", "Zero-value row needs verification.", True)
    if "..." in tx.description or "…" in tx.description:
        return Decision(
            C.REVIEW,
            Kind.UNKNOWN,
            0,
            "review.truncated",
            "Description appears truncated; verify the original export.",
            True,
        )
    if AMBIGUOUS.search(text):
        return Decision(
            C.REVIEW,
            Kind.UNKNOWN,
            0.2,
            "review.special",
            "Cash, rewards, disputes, and reversals require context.",
            True,
        )
    # A refund attached to a transfer label is conflicting evidence, not an ordinary transfer.
    if TRANSFER.search(text) and not REFUND.search(text):
        return Decision(
            C.TRANSFERS,
            Kind.TRANSFER,
            0.99,
            "movement.transfer",
            "Explicit transfer or card payment; excluded from income and expenses.",
        )
    merchant = re.sub(r"^(?:REFUND|REFUNDED|RETURN|RETURNED)\s+", "", text)
    matches = [rule for rule in MERCHANT_RULES if re.search(rule.pattern, merchant)]
    if len({rule.category for rule in matches}) > 1:
        return Decision(
            C.REVIEW, Kind.UNKNOWN, 0.2, "review.conflict", "Merchant rules disagree; human review is required.", True
        )
    if tx.amount_minor > 0:
        if REFUND.search(text):
            if matches:
                rule = max(matches, key=lambda item: item.strength)
                return Decision(
                    rule.category,
                    Kind.REFUND,
                    0.93,
                    "refund." + rule.id,
                    "Explicit merchant refund reduces this expense category; it is not income. " + rule.explanation,
                    rule.review,
                )
            return Decision(
                C.REVIEW,
                Kind.REFUND,
                0.5,
                "review.refund",
                "Refund detected, but its original expense category is unknown.",
                True,
            )
        return Decision(
            C.REVIEW,
            Kind.UNKNOWN,
            0.1,
            "review.credit",
            "Money in could be client income, a refund, or a transfer. Confirm its source.",
            True,
        )
    if REFUND.search(text):
        return Decision(
            C.REVIEW,
            Kind.UNKNOWN,
            0.1,
            "review.sign",
            "Refund wording conflicts with money-out direction. Check the amount convention.",
            True,
        )
    if matches:
        rule = max(matches, key=lambda item: item.strength)
        return Decision(rule.category, Kind.EXPENSE, rule.strength, rule.id, rule.explanation, rule.review)
    return Decision(
        C.REVIEW,
        Kind.UNKNOWN,
        0,
        "review.unknown",
        "No sufficiently specific rule matched. Confirm the receipt and business purpose.",
        True,
    )
