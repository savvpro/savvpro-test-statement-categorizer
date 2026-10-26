"""The categorization brain: deterministic, explainable rules. No ML model.

The engine only orchestrates. What a row *is* is decided by the classifier
chain, whether a verdict is *trusted* by the confidence policy, and
statement-wide signals by post-processors. All three are injected.
"""
from typing import List, Sequence

from ..domain.models import CategorizedTransaction, Category, RawTransaction
from .classifiers import Classifier
from .context import Decision, StatementLedger, TransactionContext
from .post_processors import PostProcessor


class ConfidencePolicy:
    """A wrong guess is worse than asking: weak verdicts become Needs Review."""

    def __init__(self, threshold: float):
        self._threshold = threshold

    def apply(self, decision: Decision) -> Decision:
        if decision.category == Category.NEEDS_REVIEW or decision.confidence >= self._threshold:
            return decision
        return Decision.review(f"Low confidence ({decision.reasons[0]})", suggestion=decision.category,
                               confidence=decision.confidence, flags=decision.flags)


class CategorizationEngine:
    def __init__(self, classifiers: Sequence[Classifier], policy: ConfidencePolicy,
                 post_processors: Sequence[PostProcessor] = ()):
        if not classifiers:
            raise ValueError("At least one classifier is required")
        self._classifiers = list(classifiers)
        self._policy = policy
        self._post_processors = list(post_processors)

    def categorize(self, transactions: List[RawTransaction]) -> List[CategorizedTransaction]:
        ledger = StatementLedger()
        results = {}
        # Chronological order so refunds can find the purchase they reverse.
        for tx in sorted(transactions, key=lambda t: (t.date, t.row)):
            ctx = TransactionContext.build(tx, ledger)
            decision = self._policy.apply(self._decide(ctx))
            result = CategorizedTransaction(
                **tx.model_dump(), merchant=ctx.merchant, category=decision.category,
                confidence=round(decision.confidence, 2), reasons=list(decision.reasons),
                flags=list(decision.flags), suggestion=decision.suggestion, refund_of=decision.refund_of,
            )
            ledger.record(ctx.fingerprint, result)
            results[tx.row] = result

        ordered = [results[t.row] for t in transactions]  # back to statement order
        for processor in self._post_processors:
            ordered = processor.process(ordered)
        return ordered

    def _decide(self, ctx: TransactionContext) -> Decision:
        for classifier in self._classifiers:
            decision = classifier.classify(ctx)
            if decision is not None:
                return decision
        return Decision.review("No classifier could decide")
