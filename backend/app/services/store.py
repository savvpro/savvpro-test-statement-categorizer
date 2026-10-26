"""In-memory upload sessions and the learned-corrections memory.

Data lives only for the life of the server process (no database, by design for
this assessment). See DESIGN.md for the trade-off.
"""
import threading
import uuid
from dataclasses import dataclass, field

from app.categorizer import SPEND_RULES, categorize, merchant_key, normalize
from app.models import CategorizedTransaction, Transaction

ASSIGNABLE_CATEGORIES: list[str] = [
    *SPEND_RULES,
    "Personal",
    "Income",
    "Refund",
    "Credit",
    "Transfer",
]


@dataclass
class Row:
    result: CategorizedTransaction
    duplicate_of: int | None = None
    duplicate_overridden: bool = False
    user_corrected: bool = False

    @property
    def is_duplicate(self) -> bool:
        return self.duplicate_of is not None and not self.duplicate_overridden


@dataclass
class Session:
    id: str
    filename: str
    rows: dict[int, Row] = field(default_factory=dict)


class Store:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self.memory: dict[str, str] = {}
        self._lock = threading.RLock()

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self.memory.clear()

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def create(self, filename: str, txns: list[Transaction]) -> Session:
        with self._lock:
            session = Session(id=uuid.uuid4().hex, filename=filename)
            seen: dict[tuple, int] = {}
            for row_id, txn in enumerate(txns, start=1):
                row = Row(result=categorize(txn, self.memory))
                if txn.is_valid and txn.txn_date is not None:
                    key = (txn.txn_date, normalize(txn.description), txn.amount, txn.currency)
                    if key in seen:
                        row.duplicate_of = seen[key]
                    else:
                        seen[key] = row_id
                session.rows[row_id] = row
            self._sessions[session.id] = session
            return session

    def correct(self, session: Session, row_id: int, category: str) -> int:
        """Apply a user correction. Returns how many OTHER rows were updated too."""
        with self._lock:
            row = session.rows[row_id]
            key = merchant_key(row.result.transaction.description)
            self._apply(row, category)
            updated = 0
            txn = row.result.transaction

            # Learn only ordinary outgoing merchant expenses.
            # Never propagate incoming credits, refunds or transfers.
            can_learn = (
                bool(key)
                and txn.is_valid
                and txn.amount is not None
                and txn.amount > 0
                and category in SPEND_RULES
                and not any(
                    word in normalize(txn.description)
                    for word in (
                        "REFUND", "REVERSAL", "CHARGEBACK",
                        "TRANSFER TO", "TRANSFER FROM", "OWN ACCOUNT",
                    )
                )
            )

            if can_learn:
                self.memory[key] = category
                for other_id, other in session.rows.items():
                    other_txn = other.result.transaction
                    if (
                        other_id != row_id
                        and other.result.needs_review
                        and not other.user_corrected
                        and other_txn.is_valid
                        and other_txn.amount is not None
                        and other_txn.amount > 0
                        and merchant_key(other_txn.description) == key
                    ):
                        self._apply(other, category)
                        updated += 1
            return updated

    def set_keep_duplicate(self, row: Row, keep: bool) -> None:
        with self._lock:
            row.duplicate_overridden = keep

    @staticmethod
    def _apply(row: Row, category: str) -> None:
        row.result = row.result.model_copy(
            update={
                "category": category,
                "confidence": 1.0,
                "reason": "Set by you",
                "needs_review": False,
                "matched_rule": "user",
            }
        )
        row.user_corrected = True


store = Store()
