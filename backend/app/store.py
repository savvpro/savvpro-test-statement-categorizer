"""In-memory store for transactions and overrides.

No database — transactions live in a dict keyed by id. Suitable for a
single-user take-home app. Production would use Postgres (see DESIGN.md).
"""

from typing import Optional

from app.brain.overrides import OverrideStore
from app.models import Transaction


class TransactionStore:
    """Thread-unsafe in-memory store (single-user app)."""

    def __init__(self) -> None:
        self._transactions: dict[str, Transaction] = {}
        self._order: list[str] = []  # preserve insertion order
        self.overrides = OverrideStore()

    def add(self, transaction: Transaction) -> None:
        self._transactions[transaction.id] = transaction
        self._order.append(transaction.id)

    def get(self, tx_id: str) -> Optional[Transaction]:
        return self._transactions.get(tx_id)

    def list_all(self) -> list[Transaction]:
        return [self._transactions[tid] for tid in self._order]

    def update_category(self, tx_id: str, category: str) -> Optional[Transaction]:
        tx = self._transactions.get(tx_id)
        if tx is None:
            return None
        updated = Transaction(
            id=tx.id,
            date=tx.date,
            description=tx.description,
            amount=tx.amount,
            category=category,
            confidence=1.0,
            reason="user correction",
            needs_review=False,
            is_duplicate=tx.is_duplicate,
        )
        self._transactions[tx_id] = updated

        # Persist as a merchant override for future uploads
        from app.brain.normalizer import normalize
        norm = normalize(tx.description)
        if norm:
            self.overrides.set(norm, category)

        return updated

    def clear(self) -> None:
        self._transactions.clear()
        self._order.clear()
        self.overrides.clear()

    def clear_transactions(self) -> None:
        self._transactions.clear()
        self._order.clear()

    def __len__(self) -> int:
        return len(self._transactions)


# Global store instance
store = TransactionStore()
