"""THE BRAIN: plain Python, no AI model.

Every transaction goes through the same ordered steps and always comes out with a
category, a confidence and a human-readable reason. Anything the brain cannot justify
becomes "Needs Review". A wrong guess costs the driver money at tax time; asking costs
them ten seconds.

Order of the steps (first one that decides wins):

  0. Unreadable / zero-amount lines      -> review
  1. Something the user already taught   -> that category
  2. Structural: transfers, card payments (money moving, not spending)
  3. Cash and wallets (ATM, Easypaisa)    -> review, the purpose is unknowable
  4. Money IN: payout -> Income, refund wording -> Refund, otherwise review
  5. Money OUT: keyword rules, conflicts -> review, weak matches -> review
  6. Fuzzy match against what the user taught (typos, small variations)
  7. Nothing matched                      -> review
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from rapidfuzz import fuzz, process

from ..categories import DEDUCTIBLE, Category, sign_allows
from ..models import Decision
from .normalizer import normalize
from .rules import Rule, Rules, load_rules

REFUND_CONFIDENCE = 0.9


@dataclass(frozen=True)
class _Hit:
    rule: Rule
    text: str  # the part of the description that matched, for the reason shown to the user


def _review(reason: str, confidence: float = 0.0, suggestion: Category | None = None) -> Decision:
    return Decision(
        category=Category.NEEDS_REVIEW,
        confidence=confidence,
        reason=reason,
        suggestion=suggestion,
    )


class Categorizer:
    """Stateless: what the user taught it is passed in per call (see `learned`)."""

    def __init__(self, rules: Rules | None = None) -> None:
        self.rules = rules or load_rules()

    # ------------------------------------------------------------ helpers

    def normalize(self, description: str) -> str:
        return normalize(description, self.rules.noise_words)

    def is_learnable(self, description: str) -> bool:
        """Cash and wallet rows are never remembered: each one has its own purpose."""
        key = self.normalize(description)
        return bool(key) and not self.rules.always_review.search(key)

    def related_category(self, description: str) -> Category | None:
        """For a refund: which expense category it most likely reverses."""
        hits = [
            h
            for h in self._hits(self.rules.expense, self.normalize(description))
            if h.rule.category in DEDUCTIBLE or h.rule.category is Category.PERSONAL
        ]
        if not hits:
            return None
        return max(hits, key=lambda h: h.rule.confidence).rule.category

    @staticmethod
    def _hits(rules: tuple[Rule, ...], key: str) -> list[_Hit]:
        return [_Hit(r, m.group(0)) for r in rules if (m := r.regex.search(key))]

    def _gate(self, decision: Decision) -> Decision:
        """Never auto-accept a decision weaker than the review threshold."""
        if decision.confidence >= self.rules.review_threshold:
            return decision
        pct = round(decision.confidence * 100)
        return _review(
            f"Only {pct}% sure. {decision.reason}",
            confidence=decision.confidence,
            suggestion=decision.category,
        )

    # ------------------------------------------------------------ the brain

    def categorize(
        self,
        description: str,
        amount: Decimal,
        learned: Mapping[str, Category] | None = None,
    ) -> Decision:
        rules = self.rules
        learned = learned or {}
        key = self.normalize(description)

        # 0. Nothing to work with
        if not key:
            return _review("There is nothing readable in this description.")
        if amount == 0:
            return _review("This line has a zero amount.")

        # 1. Things the user already taught us (only if the direction of the money fits)
        taught = learned.get(key)
        if taught is not None and sign_allows(taught, amount):
            return Decision(
                category=taught,
                confidence=rules.learned_confidence,
                reason="Same merchant as a row you fixed earlier.",
            )

        # 2. Money moving around, not spending
        if hits := self._hits(rules.structural, key):
            best = max(hits, key=lambda h: h.rule.confidence)
            what = (
                "a card payment"
                if best.rule.category is Category.CARD_PAYMENT
                else "a transfer between accounts"
            )
            return self._gate(
                Decision(
                    category=best.rule.category,
                    confidence=best.rule.confidence,
                    reason=f"“{best.text}” is {what}, not spending.",
                )
            )

        # 3. Cash and wallets: only the driver knows what it was for
        if cash := rules.always_review.search(key):
            return _review(
                f"“{cash.group(0)}” is cash or a wallet transfer. "
                "Nothing on the statement says what it was for.",
                confidence=0.2,
            )

        if amount > 0:
            return self._money_in(key)
        return self._money_out(key, amount, learned)

    def _money_in(self, key: str) -> Decision:
        rules = self.rules
        income = self._hits(rules.income, key)
        refund = rules.refund_words.search(key)

        if income and refund:
            return _review(
                "Has both payout and refund wording. Income and refunds are taxed "
                "differently, so please confirm.",
                confidence=0.3,
            )
        if income:
            best = max(income, key=lambda h: h.rule.confidence)
            return Decision(
                category=Category.INCOME,
                confidence=best.rule.confidence,
                reason=f"“{best.text}” is a platform payout.",
            )
        if refund:
            related = self.related_category(key)
            note = f" It looks like a refund of {related.value}." if related else ""
            return Decision(
                category=Category.REFUND,
                confidence=REFUND_CONFIDENCE,
                reason=f"“{refund.group(0)}” means money back, not income.{note}",
                related_category=related,
            )
        if shop := self._hits(rules.expense, key):
            return _review(
                f"Money in from “{shop[0].text}”, a merchant you normally pay. "
                "Could be a refund, but the statement does not say so.",
                confidence=0.4,
                suggestion=Category.REFUND,
            )
        return _review(
            "Money in from a source I do not recognise. Income and refunds are "
            "taxed differently, so please confirm.",
            confidence=0.3,
        )

    def _money_out(self, key: str, amount: Decimal, learned: Mapping[str, Category]) -> Decision:
        rules = self.rules

        if payout := self._hits(rules.income, key):
            return _review(
                f"“{payout[0].text}” is normally money in, but this money went out. "
                "Could be a reversal or clawback.",
                confidence=0.3,
            )
        if refund := rules.refund_words.search(key):
            return _review(
                f"“{refund.group(0)}” is normally money back, but this money went out.",
                confidence=0.3,
            )

        # 5. Keyword rules
        if hits := self._hits(rules.expense, key):
            categories = {h.rule.category for h in hits}
            if len(categories) > 1:
                names = ", ".join(sorted(c.value for c in categories))
                return _review(f"Matches more than one category ({names}).", confidence=0.4)
            best = max(hits, key=lambda h: h.rule.confidence)
            return self._gate(
                Decision(
                    category=best.rule.category,
                    confidence=best.rule.confidence,
                    reason=f"“{best.text}” → {best.rule.category.value}.",
                )
            )

        # 6. Fuzzy match against what the user taught (handles typos and variations)
        candidates = {k: c for k, c in learned.items() if sign_allows(c, amount)}
        if candidates:
            found = process.extractOne(
                key,
                list(candidates),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=rules.fuzzy_min_score,
            )
            if found is not None:
                match, score, _ = found
                return self._gate(
                    Decision(
                        category=candidates[match],
                        confidence=round(score / 100 * rules.fuzzy_scale, 2),
                        reason=(
                            f"Looks like “{match}”, which you filed under "
                            f"{candidates[match].value} ({round(score)}% similar)."
                        ),
                    )
                )

        # 7. No idea
        return _review(f"I do not recognise “{key.title()}”.")
