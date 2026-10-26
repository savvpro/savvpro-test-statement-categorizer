"""The brain: deterministic, rule-based decisions with explanations.

No AI model is involved. Every decision comes from the readable rules in
rules.py, and when the evidence is weak or conflicting the row goes to
Needs Review instead of being guessed.
"""
import re
from decimal import Decimal

from rapidfuzz import fuzz

from app.brain import rules as R
from app.brain.mortgage import LoanMismatchError, split_payment
from app.brain.normalize import normalize
from app.models import (
    CategorizedTransaction,
    Category,
    LoanDetails,
    RawTransaction,
    Split,
)

THRESHOLD = 0.75        # below this we ask the user instead of guessing
CONFLICT_MARGIN = 0.10  # two categories this close = we are not sure
FUZZY_MIN_RATIO = 88    # 0-100, how similar a typo must be to count
FUZZY_DISCOUNT = 0.90   # a fuzzy match is trusted a bit less than an exact one

Decision = tuple[Category, float, str]  # category, confidence, explanation


def _contains(text: str, phrase: str) -> bool:
    """Whole-word / whole-phrase match, so RENT does not match CURRENT."""
    pattern = rf"(?<![A-Z0-9]){re.escape(phrase)}(?![A-Z0-9])"
    return re.search(pattern, text) is not None


def _first_match(text: str, phrases) -> str | None:
    return next((p for p in phrases if _contains(text, p)), None)


def _score(text: str, amount: Decimal) -> dict[Category, tuple[float, list[str]]]:
    """Score every category: several independent hints add up (noisy-OR)."""
    tokens = text.split()
    hits: dict[Category, list[tuple[float, str]]] = {}

    for rule in R.RULES:
        if rule.direction == R.IN and amount <= 0:
            continue
        if _contains(text, rule.keyword):
            hits.setdefault(rule.category, []).append((rule.weight, rule.keyword))
        elif " " not in rule.keyword and len(rule.keyword) >= 5:
            # Typo tolerance for single words, e.g. PLUMBNG -> PLUMBING.
            for token in tokens:
                if len(token) >= 5 and fuzz.ratio(token, rule.keyword) >= FUZZY_MIN_RATIO:
                    hits.setdefault(rule.category, []).append(
                        (rule.weight * FUZZY_DISCOUNT, f"{rule.keyword}~{token}")
                    )
                    break

    scores = {}
    for category, found in hits.items():
        miss = 1.0
        for weight, _ in found:
            miss *= 1.0 - weight
        scores[category] = (min(1.0 - miss, 0.99), [label for _, label in found])
    return scores


class Categorizer:
    def __init__(self, loan: LoanDetails | None = None) -> None:
        self._learned: dict[str, Category] = {}
        self.loan = loan  # lets us split mortgage payments; None = send to review

    def learn(self, description: str, category: Category) -> None:
        """Remember a user's correction for every similar future row."""
        if category == Category.NEEDS_REVIEW:
            raise ValueError("Cannot learn 'Needs Review' as a category.")
        self._learned[normalize(description)] = category

    # ------------------------------------------------------------------
    def decide(self, description: str, amount: Decimal) -> tuple[str, Decision]:
        text = normalize(description)

        if text in self._learned:
            cat = self._learned[text]
            return text, (cat, 1.0, f"You categorized '{text}' as {cat.value} before.")

        phrase = _first_match(text, R.TRANSFER_PHRASES)
        if phrase:
            return text, (
                Category.TRANSFER, 0.95,
                f"Matched '{phrase}': a move between your own accounts, not income or spending.",
            )

        phrase = _first_match(text, R.SECURITY_DEPOSIT_PHRASES)
        if phrase:
            direction = "received" if amount > 0 else "returned"
            return text, (
                Category.SECURITY_DEPOSIT, 0.95,
                f"Matched '{phrase}': a security deposit {direction}, not income or an expense.",
            )

        phrase = _first_match(text, R.MORTGAGE_PHRASES)
        if phrase:
            return text, self._review(
                0.5,
                f"Matched '{phrase}': a mortgage payment. It needs loan details to be "
                "split into interest and principal.",
            )

        for merchant, reason in R.AMBIGUOUS_MERCHANTS.items():
            if _contains(text, merchant):
                return text, self._review(0.5, f"{merchant.title()} {reason}.")

        refund_word = _first_match(text, R.REFUND_WORDS) if amount > 0 else None
        search_text = text
        if refund_word:
            search_text = " ".join(w for w in text.split() if w not in R.REFUND_WORDS)

        scores = _score(search_text, amount)
        if not scores:
            return text, self._review(0.0, "No rule matched this merchant.")

        ranked = sorted(scores.items(), key=lambda kv: kv[1][0], reverse=True)
        best_cat, (best, labels) = ranked[0]

        if best < THRESHOLD:
            return text, self._review(
                best, f"Only a weak match for {best_cat.value} ({best:.2f}): {', '.join(labels)}."
            )
        if len(ranked) > 1:
            second_cat, (second, _) = ranked[1]
            if second >= THRESHOLD and best - second < CONFLICT_MARGIN:
                return text, self._review(
                    best, f"Conflicting evidence: {best_cat.value} ({best:.2f}) vs "
                          f"{second_cat.value} ({second:.2f}).",
                )

        matched = ", ".join(labels)
        if refund_word:
            if best_cat in R.EXPENSE_CATEGORIES:
                return text, (
                    best_cat, best,
                    f"Refund ('{refund_word}') from a {best_cat.value} merchant ({matched}): "
                    "money back, so it reduces the expense and is not income.",
                )
            return text, self._review(best, "A refund that does not match an expense merchant.")

        if best_cat in R.EXPENSE_CATEGORIES and amount > 0:
            return text, self._review(
                best, f"Money came IN from a {best_cat.value} merchant ({matched}). "
                      "It may be a refund or credit, so please check.",
            )

        return text, (best_cat, best, f"Matched {matched} -> {best_cat.value} ({best:.2f}).")

    @staticmethod
    def _review(confidence: float, why: str) -> Decision:
        return Category.NEEDS_REVIEW, round(confidence, 2), why

    # ------------------------------------------------------------------
    def _try_mortgage_split(
        self, tx: RawTransaction, matched: dict[int, int]
    ) -> tuple[float, str, list[Split]]:
        """Split a mortgage payment using the loan details.

        Raises LoanMismatchError when it cannot be matched to the schedule.
        """
        scheduled = split_payment(self.loan, tx.date, -tx.amount)
        if scheduled.number in matched:
            raise LoanMismatchError(
                f"Payment #{scheduled.number} was already matched by row "
                f"{matched[scheduled.number]}."
            )
        matched[scheduled.number] = tx.row_number
        splits = [
            Split(category=Category.MORTGAGE_INTEREST, amount=-scheduled.interest),
            Split(category=Category.MORTGAGE_PRINCIPAL, amount=-scheduled.principal),
        ]
        why = (
            f"Mortgage payment #{scheduled.number} of {self.loan.term_months}, split from "
            f"your loan details: interest {scheduled.interest}, principal "
            f"{scheduled.principal}."
        )
        return 0.95, why, splits

    # ------------------------------------------------------------------
    def categorize_all(self, transactions: list[RawTransaction]) -> list[CategorizedTransaction]:
        results: list[CategorizedTransaction] = []
        seen: dict[tuple, int] = {}
        matched_payments: dict[int, int] = {}  # payment number -> row number

        for index, tx in enumerate(transactions, start=1):
            text, (category, confidence, explanation) = self.decide(tx.description, tx.amount)
            splits: list[Split] = []

            if (
                self.loan is not None
                and tx.amount < 0
                and text not in self._learned  # a manual choice always wins
                and _first_match(text, R.MORTGAGE_PHRASES)
            ):
                try:
                    confidence, explanation, splits = self._try_mortgage_split(
                        tx, matched_payments
                    )
                    category = Category.MORTGAGE_PAYMENT
                except LoanMismatchError as exc:
                    explanation = f"Mortgage payment could not be split: {exc}"

            key = (tx.date, tx.description, tx.amount)
            is_duplicate = key in seen
            if is_duplicate:
                explanation += f" Possible duplicate of row {seen[key]}."
            else:
                seen[key] = index

            results.append(
                CategorizedTransaction(
                    id=index,
                    date=tx.date,
                    description=tx.description,
                    normalized=text,
                    amount=tx.amount,
                    category=category,
                    confidence=round(confidence, 2),
                    explanation=explanation,
                    is_duplicate=is_duplicate,
                    splits=splits,
                )
            )
        return results