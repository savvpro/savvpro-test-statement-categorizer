"""Statement-level analysis that runs after every row has a decision."""
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Protocol

from ..domain.models import ALLOWABLE_EXPENSES, CategorizedTransaction, Category


class PostProcessor(Protocol):
    def process(self, results: List[CategorizedTransaction]) -> List[CategorizedTransaction]: ...


def _with_flag(tx: CategorizedTransaction, flag: str, reason: str) -> CategorizedTransaction:
    if flag in tx.flags:
        return tx
    return tx.model_copy(update={"flags": tx.flags + [flag], "reasons": tx.reasons + [reason]})


class LargeAmountFlagger:
    """Big purchases may be capital assets (capital allowances), not day-to-day expenses."""

    def __init__(self, threshold: Decimal):
        self._threshold = threshold

    def process(self, results: List[CategorizedTransaction]) -> List[CategorizedTransaction]:
        return [
            _with_flag(t, "large-amount", "Large purchase: check whether it is a capital asset")
            if self._applies(t) else t
            for t in results
        ]

    def _applies(self, tx: CategorizedTransaction) -> bool:
        could_be_expense = tx.category in ALLOWABLE_EXPENSES or tx.category == Category.NEEDS_REVIEW
        return could_be_expense and tx.amount < 0 and abs(tx.amount) >= self._threshold


class RecurringDetector:
    """Same merchant, similar amount, in 2+ different months -> a subscription to keep an eye on."""

    def __init__(self, tolerance: Decimal = Decimal("0.10")):
        self._tolerance = tolerance

    def process(self, results: List[CategorizedTransaction]) -> List[CategorizedTransaction]:
        by_merchant: Dict[str, List[CategorizedTransaction]] = defaultdict(list)
        for t in results:
            if t.amount < 0 and "duplicate" not in t.flags:
                by_merchant[t.merchant].append(t)

        recurring_rows = set()
        for txs in by_merchant.values():
            months = {(t.date.year, t.date.month) for t in txs}
            if len(months) < 2:
                continue
            reference = abs(txs[0].amount)
            if all(abs(abs(t.amount) - reference) <= reference * self._tolerance for t in txs):
                recurring_rows.update(t.row for t in txs)

        return [
            _with_flag(t, "recurring", "Recurring monthly payment") if t.row in recurring_rows else t
            for t in results
        ]
