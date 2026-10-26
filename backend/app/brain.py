"""The brain: decides a category for every transaction, or says it is not sure.

No AI model is used. The steps, in order:
1. Normalise the description into a merchant name.
2. User memory: if the user already filed this merchant, use that (highest trust).
3. Money-movement checks: card payments and transfers are not spending.
4. Refunds: a credit that looks like a refund is money back, linked to the
   original purchase's category when we can find it. Never income.
5. Credits that are not refunds/transfers: client income only if it looks like
   an invoice/payout; a P2P credit is ambiguous and goes to review.
6. Merchant rules: score every matching rule. Conflicting matches or a weak best
   match go to review.
7. Sanity flags (duplicates, unusually large amounts) can force review.
If confidence is below REVIEW_THRESHOLD the row is filed under Needs Review,
with the best guess kept as a suggestion. A wrong guess is worse than asking.
"""
from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

from . import rules
from .models import Category, Decision, Kind, RawTransaction

REVIEW_THRESHOLD = 0.7
LARGE_AMOUNT = Decimal("2000")

_NOISE = [
    r"^(pos|debit card|dbt crd|purchase|recurring|checkcard|visa|ach)( purchase)?\s+",
    r"\b(sq|tst|pp|sp)\s*\*\s*",       # Square / Toast / PayPal / Shopify prefixes
    r"#\s*\d+",                        # store numbers
    r"\b\d{2}/\d{2}(/\d{2,4})?\b",     # embedded dates
    r"\b[a-z]{2} \d{5}\b",             # state + zip
    r"\bx{2,}\d+\b",                   # masked card numbers
    r"\b\d{4,}\b",                     # long reference numbers
    r"[*]+",
]


def normalise_merchant(description: str) -> str:
    m = description.lower()
    for pattern in _NOISE:
        m = re.sub(pattern, " ", m)
    m = re.sub(r"[^a-z0-9&.+' -]", " ", m)
    return " ".join(m.split()).strip(" .-") or description.lower().strip()


def merchant_key(merchant: str) -> str:
    """Short stable key used for user memory and refund matching (first 2 words)."""
    return " ".join(merchant.split()[:2])


class Brain:
    def __init__(self, memory: dict[str, Category] | None = None):
        # merchant_key -> category the user chose. Shared across uploads.
        self.memory: dict[str, Category] = memory if memory is not None else {}

    def learn(self, merchant: str, category: Category) -> None:
        if category != Category.NEEDS_REVIEW:
            self.memory[merchant_key(merchant)] = category

    # ---- single row --------------------------------------------------
    def decide(self, tx: RawTransaction, merchant: str, history: dict[str, Category]) -> Decision:
        desc = tx.description
        key = merchant_key(merchant)

        if rules.CARD_PAYMENT.search(desc):
            return Decision(Category.CARD_PAYMENT, 0.95, "Paying off the card is not spending.")
        if rules.TRANSFER.search(desc):
            return Decision(Category.TRANSFER, 0.9, "Moving money between own accounts is not spending.")

        if tx.kind == Kind.CREDIT:
            return self._decide_credit(tx, merchant, key, history)

        if key in self.memory:
            return Decision(self.memory[key], 0.97, f"You filed '{key}' as this before.")

        if rules.AMBIGUOUS_MERCHANTS.search(merchant):
            guess = self._match_rules(merchant)
            return Decision(
                Category.NEEDS_REVIEW, 0.4,
                "This store sells both business and personal items; please choose.",
                flags=["ambiguous_merchant"],
            ) if guess is None else Decision(
                Category.NEEDS_REVIEW, 0.5, "Mixed-use store; best guess shown as suggestion.",
                flags=["ambiguous_merchant", f"suggest:{guess[0].value}"],
            )

        match = self._match_rules(merchant)
        if match is None:
            return Decision(Category.NEEDS_REVIEW, 0.0, "Unknown merchant; no rule matched.")
        category, confidence, reason = match
        return Decision(category, confidence, reason)

    def _decide_credit(self, tx: RawTransaction, merchant: str, key: str, history: dict[str, Category]) -> Decision:
        if rules.REFUND.search(tx.description) or key in history:
            original = history.get(key) or (self._match_rules(merchant) or (None,))[0]
            if original and original not in (Category.NEEDS_REVIEW, Category.CLIENT_INCOME):
                return Decision(original, 0.85, f"Refund from a {original.value} purchase; reduces that category, not income.", is_refund=True)
            return Decision(Category.NEEDS_REVIEW, 0.5, "Money back, but the original purchase category is unknown.", is_refund=True)
        if rules.CLIENT_INCOME.search(tx.description):
            return Decision(Category.CLIENT_INCOME, 0.9, "Looks like a client payment / payout.")
        if rules.P2P_INCOME.search(tx.description):
            return Decision(Category.NEEDS_REVIEW, 0.5, "Person-to-person money in: could be a client or a friend paying back.")
        if key in self.memory and self.memory[key] == Category.CLIENT_INCOME:
            return Decision(Category.CLIENT_INCOME, 0.95, f"You filed '{key}' as client income before.")
        return Decision(Category.NEEDS_REVIEW, 0.3, "Money in that is not clearly income, a refund or a transfer.")

    @staticmethod
    def _match_rules(merchant: str) -> tuple[Category, float, str] | None:
        scores: dict[Category, float] = defaultdict(float)
        for pattern, category, strength in rules.MERCHANT_RULES:
            if pattern.search(merchant):
                scores[category] = max(scores[category], strength)
        if not scores:
            return None
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_cat, best = ranked[0]
        if len(ranked) > 1 and ranked[1][1] >= best - 0.15:
            # Two categories fit about equally well: do not guess.
            return best_cat, min(best, 0.5), f"Matches both {best_cat.value} and {ranked[1][0].value}."
        return best_cat, best, f"Merchant rule matched ({best_cat.value})."

    # ---- whole statement --------------------------------------------
    def categorise(self, txs: list[RawTransaction]) -> list[tuple[RawTransaction, str, Decision]]:
        """Processes rows oldest-first so refunds can link to earlier purchases."""
        history: dict[str, Category] = {}
        seen: dict[tuple, int] = {}
        out = []
        for tx in sorted(txs, key=lambda t: (t.date, t.row_number)):
            merchant = normalise_merchant(tx.description)
            decision = self.decide(tx, merchant, history)

            dup_key = (tx.date, merchant, tx.amount, tx.kind)
            if dup_key in seen:
                decision.flags.append(f"possible_duplicate_of_row:{seen[dup_key]}")
                decision.reason += " Same date, merchant and amount as another row; possible duplicate."
                decision.confidence = min(decision.confidence, 0.5)
            seen.setdefault(dup_key, tx.row_number)

            if tx.amount >= LARGE_AMOUNT and tx.kind == Kind.DEBIT and decision.category not in rules_non_spend():
                decision.flags.append("large_amount")
                decision.reason += " Large purchase; please confirm (may need to be depreciated)."
                decision.confidence = min(decision.confidence, 0.6)

            if decision.confidence < REVIEW_THRESHOLD and decision.category != Category.NEEDS_REVIEW:
                decision.flags.append(f"suggest:{decision.category.value}")
                decision.category = Category.NEEDS_REVIEW

            if tx.kind == Kind.DEBIT and decision.category != Category.NEEDS_REVIEW:
                history[merchant_key(merchant)] = decision.category
            out.append((tx, merchant, decision))
        return out


def rules_non_spend() -> set[Category]:
    return {Category.TRANSFER, Category.CARD_PAYMENT}
