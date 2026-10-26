"""In-memory store for uploaded statements.

Simple on purpose: this app has no accounts or database. Each upload gets
an id; the oldest uploads are evicted so memory cannot grow without limit.
Swap this class for a database-backed one to persist across restarts.
"""
import uuid
from dataclasses import dataclass

from app.brain.categorizer import Categorizer
from app.models import CategorizedTransaction, LoanDetails, RawTransaction
from app.parsing.csv_parser import RowError

MAX_STATEMENTS = 100


@dataclass
class StatementSession:
    id: str
    filename: str
    raw: list[RawTransaction]
    parse_errors: list[RowError]
    categorizer: Categorizer
    results: list[CategorizedTransaction]

    def recompute(self) -> None:
        self.results = self.categorizer.categorize_all(self.raw)

    def set_loan(self, loan: LoanDetails | None) -> None:
        self.categorizer.loan = loan
        self.recompute()


class StatementStore:
    def __init__(self) -> None:
        self._sessions: dict[str, StatementSession] = {}

    def create(
        self,
        filename: str,
        raw: list[RawTransaction],
        parse_errors: list[RowError],
        loan: LoanDetails | None,
    ) -> StatementSession:
        categorizer = Categorizer(loan=loan)
        session = StatementSession(
            id=uuid.uuid4().hex,
            filename=filename,
            raw=raw,
            parse_errors=parse_errors,
            categorizer=categorizer,
            results=categorizer.categorize_all(raw),
        )
        self._sessions[session.id] = session
        while len(self._sessions) > MAX_STATEMENTS:
            self._sessions.pop(next(iter(self._sessions)))  # oldest first
        return session

    def get(self, statement_id: str) -> StatementSession | None:
        return self._sessions.get(statement_id)


_store = StatementStore()


def get_store() -> StatementStore:
    """FastAPI dependency; tests replace it with a fresh store."""
    return _store