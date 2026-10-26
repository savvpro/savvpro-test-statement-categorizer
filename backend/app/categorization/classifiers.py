"""The classifier chain (Chain of Responsibility).

Each classifier owns one concern and either returns a `Decision` or `None`
to pass the row on. Order matters and is defined in one place: `factory.py`.
Adding a behaviour means adding a class, not editing the engine.
"""
from typing import Optional, Protocol

from ..domain.models import Category, fits_direction
from ..learning.repository import MerchantRuleRepository
from .context import Decision, TransactionContext
from .rulebook import RuleBook, contains_any


class Classifier(Protocol):
    def classify(self, ctx: TransactionContext) -> Optional[Decision]: ...


class DuplicateClassifier:
    def classify(self, ctx: TransactionContext) -> Optional[Decision]:
        first = ctx.ledger.seen.get(ctx.fingerprint)
        if first is None:
            return None
        return Decision.review(f"Possible duplicate of row {first}", flags=("duplicate",))


class LearnedRuleClassifier:
    """The user's own corrections beat built-in knowledge."""

    def __init__(self, repository: MerchantRuleRepository):
        self._repository = repository

    def classify(self, ctx: TransactionContext) -> Optional[Decision]:
        rule = self._repository.get(ctx.merchant)
        if rule is None or not fits_direction(rule.category, ctx.tx.amount):
            return None
        return Decision(rule.category, 1.0, (f"Your saved rule for '{ctx.merchant}'",), ("learned",))


class TransferClassifier:
    def __init__(self, rules: RuleBook):
        self._rules = rules

    def classify(self, ctx: TransactionContext) -> Optional[Decision]:
        if not contains_any(ctx.text, self._rules.transfer):
            return None
        return Decision(Category.TRANSFER, 0.95,
                        ("Movement between own accounts or card repayment, not income or spending",))


class RefundClassifier:
    """Money back is never income: it offsets the original expense."""

    def __init__(self, rules: RuleBook):
        self._rules = rules

    def classify(self, ctx: TransactionContext) -> Optional[Decision]:
        if not ctx.is_credit:
            return None
        original = ctx.ledger.take_refundable(ctx.merchant, ctx.tx.amount)
        if original is not None:
            return Decision(original.category, 0.9,
                            (f"Refund matched to purchase on row {original.row}; offsets that expense",),
                            ("refund",), refund_of=original.row)
        if contains_any(ctx.text, self._rules.refund):
            return Decision(Category.REFUND, 0.8,
                            ("Refund wording but no matching purchase on this statement; "
                             "treated as money back, not income",), ("refund",))
        return None


class CreditClassifier:
    def __init__(self, rules: RuleBook):
        self._rules = rules

    def classify(self, ctx: TransactionContext) -> Optional[Decision]:
        if not ctx.is_credit:
            return None
        if contains_any(ctx.text, self._rules.non_income_credit):
            return Decision.review("Money in that is usually not trading income (interest, salary, tax, loan)")
        if contains_any(ctx.text, self._rules.income):
            return Decision(Category.INCOME, 0.85, ("Money in with client-payment wording",))
        return Decision.review("Unexplained money in: could be income, a gift, a loan or a personal transfer",
                               suggestion=Category.INCOME, confidence=0.4)


class MixedUseClassifier:
    """Merchants selling both business and personal goods are never guessed."""

    def __init__(self, rules: RuleBook):
        self._rules = rules

    def classify(self, ctx: TransactionContext) -> Optional[Decision]:
        if ctx.is_credit or not contains_any(ctx.text, self._rules.mixed_use):
            return None
        return Decision.review("Mixed-use merchant: could be business or personal, check the receipt",
                               flags=("mixed-use",))


class KeywordClassifier:
    def __init__(self, rules: RuleBook, ambiguity_margin: float):
        self._rules = rules
        self._margin = ambiguity_margin

    def classify(self, ctx: TransactionContext) -> Optional[Decision]:
        if ctx.is_credit:
            return None
        matches = self._rules.best_matches(ctx.text)
        if not matches:
            return None
        top = matches[0]
        if len(matches) > 1 and top.weight - matches[1].weight < self._margin:
            return Decision.review(
                f"Conflicting signals: {top.category.value} vs {matches[1].category.value}",
                suggestion=top.category, confidence=top.weight / 2)
        return Decision(top.category, top.weight, (f"Matched '{top.pattern}'",))


class FallbackClassifier:
    def classify(self, ctx: TransactionContext) -> Optional[Decision]:
        return Decision.review("Unknown merchant")
