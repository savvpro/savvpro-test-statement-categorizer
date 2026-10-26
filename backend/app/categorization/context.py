"""Value objects passed through the classifier chain."""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, List, Optional, Tuple

from ..domain.models import CategorizedTransaction, Category, RawTransaction
from .normalizer import merchant_key, normalize


@dataclass(frozen=True)
class Decision:
    """A classifier's verdict, with the evidence behind it."""

    category: Category
    confidence: float
    reasons: Tuple[str, ...]
    flags: Tuple[str, ...] = ()
    suggestion: Optional[Category] = None
    refund_of: Optional[int] = None

    @classmethod
    def review(cls, reason: str, suggestion: Optional[Category] = None, confidence: float = 0.0,
               flags: Tuple[str, ...] = ()) -> "Decision":
        return cls(Category.NEEDS_REVIEW, confidence, (reason,), flags, suggestion)


@dataclass
class StatementLedger:
    """Statement-wide memory: rows already seen and purchases open for refund."""

    seen: Dict[tuple, int] = field(default_factory=dict)
    open_purchases: DefaultDict[str, List[CategorizedTransaction]] = field(
        default_factory=lambda: defaultdict(list))

    def record(self, fingerprint: tuple, result: CategorizedTransaction) -> None:
        self.seen.setdefault(fingerprint, result.row)
        refundable = result.amount < 0 and result.category not in (Category.NEEDS_REVIEW, Category.TRANSFER)
        if refundable:
            self.open_purchases[result.merchant].append(result)

    def take_refundable(self, merchant: str, amount) -> Optional[CategorizedTransaction]:
        """Pop the earliest purchase from this merchant that is at least as large as the refund."""
        purchases = self.open_purchases.get(merchant, [])
        for purchase in purchases:
            if abs(purchase.amount) >= amount:
                purchases.remove(purchase)  # a purchase can only be refunded once
                return purchase
        return None


@dataclass(frozen=True)
class TransactionContext:
    tx: RawTransaction
    text: str
    merchant: str
    ledger: StatementLedger

    @classmethod
    def build(cls, tx: RawTransaction, ledger: StatementLedger) -> "TransactionContext":
        text = normalize(tx.description)
        return cls(tx=tx, text=text, merchant=merchant_key(text), ledger=ledger)

    @property
    def is_credit(self) -> bool:
        return self.tx.amount > 0

    @property
    def fingerprint(self) -> tuple:
        return (self.tx.date, self.text, self.tx.amount)
