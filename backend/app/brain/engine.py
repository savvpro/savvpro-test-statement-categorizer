"""The decision engine: one statement row in, one explained decision out.

Layers run in order and the first one that is sure wins:

1. Learned rules  - the user's own earlier fixes for this merchant.
2. Money movement - card payments and transfers are not spending.
3. Money in       - platform payouts, tips, refunds; anything else in is unsure.
4. Fees           - bank fees and interest.
5. Merchants      - known merchants, with amount sanity checks.
6. Fallback       - unknown or ambiguous rows go to Needs Review.

Any decision under REVIEW_THRESHOLD is sent to Needs Review with its best
guess and the reason, so the user sees why the app was not sure.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.brain import rules
from app.domain.categories import NEEDS_REVIEW
from app.ingest.normalize import clean, merchant_key


@dataclass(frozen=True)
class Decision:
    category: str
    confidence: float
    reason: str
    rule: str
    suggestion: str | None = None  # best guess when sent to review

    @property
    def needs_review(self) -> bool:
        return self.category == NEEDS_REVIEW


def _review(reason: str, rule: str, suggestion: str | None = None, confidence: float = 0.0) -> Decision:
    return Decision(NEEDS_REVIEW, confidence, reason, rule, suggestion)


def _gate(category: str, confidence: float, reason: str, rule: str) -> Decision:
    if confidence < rules.REVIEW_THRESHOLD:
        return _review(f"Not sure: {reason}", rule, suggestion=category, confidence=confidence)
    return Decision(category, confidence, reason, rule)


def _is_platform(text: str) -> str | None:
    for name in rules.PLATFORMS:
        if name in text:
            return name
    return None


def learned_key(merchant: str, amount: Decimal) -> str:
    return f"{'IN' if amount > 0 else 'OUT'}:{merchant}"


def categorize(description: str, amount: Decimal, learned: dict[str, str] | None = None) -> Decision:
    text = clean(description)
    key = merchant_key(description)
    money_in = amount > 0

    # 1. The user's own fixes beat every built-in rule.
    # Keyed by direction too: filing a purchase never re-files a refund.
    lkey = learned_key(key, amount)
    if learned and lkey in learned:
        return Decision(learned[lkey], 0.97, f"You filed '{key}' as {learned[lkey]} before", "learned")

    # 2. Moving money around is not spending or income.
    if rules.CARD_PAYMENT.search(text):
        return Decision("Card Payment", 0.98, "Payment toward the card balance", "card_payment")
    if rules.TRANSFER.search(text):
        return Decision("Transfer", 0.95, "Transfer between your own accounts", "transfer")
    if rules.PEER_TO_PEER.search(text):
        return _review("Peer-to-peer payment: could be personal, a refund or business", "p2p",
                       suggestion="Transfer" if not money_in else "Platform Income", confidence=0.4)

    # 3. Money coming in.
    if money_in:
        if rules.REFUND.search(text):
            return Decision("Refund", 0.95, "Money returned for an earlier purchase", "refund")
        if rules.FOOD_ORDER.search(text) and not rules.DRIVER_SIDE.search(text):
            # Uber Eats / DoorDash credits on the driver's own order are not earnings.
            return Decision("Refund", 0.85, "Credit on your own food order, not driver earnings", "order_credit")
        platform = _is_platform(text)
        if platform and rules.BONUS.search(text):
            return Decision("Tips & Bonuses", 0.9, f"{platform} tip or bonus", "platform_bonus")
        if platform and rules.PAYOUT.search(text):
            return Decision("Platform Income", 0.95, f"{platform} driver payout", "platform_payout")
        if platform:
            return _review(f"Money in from {platform}, but not marked as a payout: could be a refund",
                           "platform_unclear", suggestion="Platform Income", confidence=0.6)
        for pattern, category, _, label in rules.MERCHANTS:
            if pattern.search(text):
                # Money back from a shop is a refund even without the word.
                return Decision("Refund", 0.85, f"Money back from a {label}", "merchant_credit")
        return _review("Money in from an unknown source: not counted as income until you confirm",
                       "unknown_credit", suggestion="Platform Income", confidence=0.3)

    # 4. Fees and interest.
    if rules.BANK_FEE.search(text) or rules.INTEREST.search(text):
        return Decision("Bank Fees", 0.9, "Bank fee or card interest", "bank_fee")
    if rules.REFUND.search(text):
        return _review("Looks like a refund but money went out: maybe a reversed refund", "refund_out",
                       confidence=0.3)

    # 5. Known merchants.
    if rules.FOOD_ORDER.search(description) and not rules.DRIVER_SIDE.search(text):
        return Decision("Meals (Personal)", 0.85, "Food delivery order you placed", "food_order")
    if rules.AMBIGUOUS.search(text):
        return _review("This store sells both business and personal items", "ambiguous_merchant",
                       suggestion="Driver Supplies", confidence=0.4)
    for pattern, category, confidence, label in rules.MERCHANTS:
        if pattern.search(text):
            if category == "Fuel" and abs(amount) < rules.FUEL_MIN_AMOUNT:
                return _review(f"Only ${abs(amount):.2f} at a {label}: probably snacks, not fuel", "small_fuel",
                               suggestion="Personal", confidence=0.5)
            return _gate(category, confidence, f"Matched {label}", f"merchant:{category}")

    # 6. Nothing matched.
    return _review(f"Unknown merchant '{key or description}'", "unknown")


def categorize_all(rows: list[tuple[str, Decimal]], learned: dict[str, str] | None = None) -> list[Decision]:
    return [categorize(desc, amount, learned) for desc, amount in rows]
