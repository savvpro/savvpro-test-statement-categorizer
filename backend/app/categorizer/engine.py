"""The brain: decides what each transaction is, or says it isn't sure.

No AI model is involved. Every decision comes from a rule in rules.yaml or a
rule the user created, and every decision carries a reason the user can read.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..parsing.values import normalize_description
from .rules import Rule, RuleBook, contains_words

AUTO = "auto"
REVIEW = "needs_review"
CORRECTED = "user_corrected"

REFUND_WINDOW_DAYS = 90
_SPECIFICITY = {"exact": 3, "starts_with": 2, "contains": 1}


@dataclass
class Txn:
    txn_date: date
    description: str
    amount: Decimal  # positive = money in
    currency: str


@dataclass
class PastTxn:
    """An earlier transaction, used to find the purchase a refund belongs to."""
    id: int
    txn_date: date
    amount: Decimal
    currency: str
    rule_id: str | None
    category: str | None
    is_refund: bool = False  # a refund line is never the purchase another refund belongs to


@dataclass
class Decision:
    status: str
    category: str | None
    suggested_category: str | None
    txn_type: str  # income | expense | transfer | refund | personal | unknown
    rule_id: str | None
    reason: str
    linked_txn_id: int | None = None


def most_specific(hits: list[Rule]) -> list[Rule]:
    best = max(_SPECIFICITY[r.match] for r in hits)
    hits = [r for r in hits if _SPECIFICITY[r.match] == best]
    # "AMAZON WEB SERVICES" is more specific than "AMAZON" when both match.
    return [
        r for r in hits
        if not any(o.pattern != r.pattern and contains_words(o.pattern, r.pattern) for o in hits)
    ]


def _type_for(kind: str) -> str:
    return {"income": "income", "expense": "expense", "tax": "expense",
            "transfer": "transfer", "personal": "personal"}.get(kind, "unknown")


def _money(amount: Decimal, currency: str) -> str:
    return f"{currency} {abs(amount):,.2f}"


class Engine:
    def __init__(self, book: RuleBook, account_type: str = "business", history: list[PastTxn] | None = None):
        if account_type not in ("business", "mixed"):
            raise ValueError("account_type must be 'business' or 'mixed'")
        self.book = book
        self.account_type = account_type
        self.history = history if history is not None else []

    def decide(self, txn: Txn, flags: list[str] | tuple = ()) -> Decision:
        decision = self._decide(txn)
        if flags:
            decision = self._hold_for_review(decision, flags)
        return decision

    # --- steps -------------------------------------------------------------

    def find_rules(self, description: str) -> tuple[str | None, list[Rule]]:
        for stage in self.book.stages:
            hits = [r for r in stage.rules if r.matches(description)]
            if hits:
                return stage.name, most_specific(hits)
        return None, []

    def _decide(self, txn: Txn) -> Decision:
        description = normalize_description(txn.description)
        _, winners = self.find_rules(description)

        if len({r.outcome for r in winners}) > 1:
            names = ", ".join(f"{r.id} says {r.category or 'review'}" for r in winners)
            return Decision(REVIEW, None, None, "unknown", winners[0].id,
                            f"Rules disagree ({names}). Turn one off or make one more specific.")

        rule = winners[0] if winners else None
        if self.book.is_refund(description):
            return self._refund(txn, rule)
        if rule is None:
            if txn.amount < 0:
                reason = "Unknown merchant. No rule matches this description."
            else:
                reason = "Money in from an unknown source. No rule matches this description."
            return Decision(REVIEW, None, None, "unknown", None, reason)
        if rule.review:
            return Decision(REVIEW, None, rule.suggest, "unknown", rule.id, rule.review)
        return self._apply(txn, rule)

    def _apply(self, txn: Txn, rule: Rule) -> Decision:
        kind = self.book.kind(rule.category)
        money_in = txn.amount > 0
        name = rule.pattern

        if kind in ("expense", "tax") and money_in:
            return Decision(REVIEW, None, rule.category, "unknown", rule.id,
                            f"{name} is normally {rule.category}, but this is money coming in "
                            "and the statement doesn't call it a refund.")
        if kind == "income" and not money_in:
            return Decision(REVIEW, None, None, "unknown", rule.id,
                            f"{name} is normally a source of income, but this is money going out.")
        if rule.business_use == "sometimes":
            return Decision(REVIEW, None, rule.category, "unknown", rule.id,
                            f"{name} can be business or personal. Suggested: {rule.category}.")
        if rule.business_use == "usually" and self.account_type == "mixed":
            return Decision(REVIEW, None, rule.category, "unknown", rule.id,
                            f"{name} is usually business, but this account mixes business and personal "
                            "spending. Please confirm.")

        if rule.source == "user":
            reason = f"Your rule: {name} is {rule.category}."
        else:
            reason = f"Matched {name}, so {rule.category} (rule {rule.id})."
        if kind == "transfer":
            reason += " Money moved between your own accounts isn't income or spending."
        elif kind == "tax":
            reason += " Tax taken by the bank is kept apart from expenses."
        elif kind == "personal":
            reason += " Personal spending isn't counted in business totals."
        elif rule.business_use == "usually":
            reason += " Counted as business because this is a business account."
        return Decision(AUTO, rule.category, None, _type_for(kind), rule.id, reason)

    def _refund(self, txn: Txn, rule: Rule | None) -> Decision:
        rule_id = rule.id if rule else None
        if txn.amount < 0:
            return Decision(REVIEW, None, None, "unknown", rule_id,
                            "The description says refund or reversal, but money went out.")
        if rule is None:
            return Decision(REVIEW, None, None, "refund", None,
                            "Refund from a merchant the app doesn't know. It won't count as income. "
                            "Pick the category it should reduce.")
        target = rule.category or rule.suggest
        kind = self.book.kind(target)
        if rule.review:
            return Decision(REVIEW, None, rule.suggest, "refund", rule.id,
                            f"Reversal of something unclear. {rule.review}")
        if kind == "transfer":
            return Decision(AUTO, target, None, "transfer", rule.id,
                            f"Reversed transfer ({rule.pattern}). Money moved between your own accounts isn't income.")
        if kind == "income":
            return Decision(REVIEW, None, None, "refund", rule.id,
                            f"A refund from {rule.pattern} is unusual, since it normally pays you. Check what this is.")

        candidates = [
            p for p in self.history
            if p.currency == txn.currency and p.amount < 0 and p.rule_id == rule.id and not p.is_refund
            and abs(p.amount) >= txn.amount and 0 <= (txn.txn_date - p.txn_date).days <= REFUND_WINDOW_DAYS
        ]
        if len(candidates) == 1:
            original = candidates[0]
            when = original.txn_date.strftime("%d %b %Y")
            if original.category is None:
                return Decision(REVIEW, None, target, "refund", rule.id,
                                f"Refund of the {when} {rule.pattern} purchase, which still needs review. "
                                "Pick the same category for both.", original.id)
            paid = _money(original.amount, original.currency)
            return Decision(AUTO, original.category, None, "refund", rule.id,
                            f"Refund of the {when} {rule.pattern} purchase ({paid}). "
                            f"It reduces {original.category} instead of counting as income.", original.id)
        if not candidates:
            return Decision(REVIEW, None, target, "refund", rule.id,
                            f"Refund from {rule.pattern}, but no matching purchase from the last "
                            f"{REFUND_WINDOW_DAYS} days was found. It won't count as income.")
        return Decision(REVIEW, None, target, "refund", rule.id,
                        f"Refund from {rule.pattern} could belong to {len(candidates)} earlier purchases, "
                        "so the app can't tell which one.")

    @staticmethod
    def _hold_for_review(decision: Decision, flags) -> Decision:
        reason = " ".join(flags)
        if decision.status == AUTO:
            reason += f" Otherwise the app would have chosen {decision.category}."
        else:
            reason += f" Also: {decision.reason}"
        return Decision(REVIEW, None, decision.category or decision.suggested_category,
                        decision.txn_type, decision.rule_id, reason, decision.linked_txn_id)
