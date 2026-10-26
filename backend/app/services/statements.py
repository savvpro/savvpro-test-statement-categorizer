"""Use cases: upload a statement, fix a row. The routes stay thin; the rules live here."""

import logging
import time
from dataclasses import dataclass

from ..brain.categorizer import Categorizer
from ..categories import Category, sign_allows
from ..models import Statement
from ..parser import parse_statement
from ..store import StatementStore

log = logging.getLogger("statement_categorizer")


class NotFoundError(LookupError):
    pass


@dataclass
class FixResult:
    statement: Statement
    updated_ids: list[str]


class StatementService:
    def __init__(self, store: StatementStore, categorizer: Categorizer, max_rows: int = 5000):
        self._store = store
        self._brain = categorizer
        self._max_rows = max_rows

    def create(
        self, filename: str, content: bytes, *, purchases_positive: bool = False
    ) -> Statement:
        started = time.perf_counter()
        parsed = parse_statement(
            content, purchases_positive=purchases_positive, max_rows=self._max_rows
        )
        for txn in parsed.transactions:
            txn.apply(self._brain.categorize(txn.description, txn.amount))
        statement = Statement(
            filename=filename,
            transactions=parsed.transactions,
            skipped=parsed.skipped,
            warnings=parsed.warnings,
        )
        self._store.add(statement)
        # Counts only: statement contents are financial data and stay out of the logs.
        log.info(
            "statement %s created: %d rows, %d skipped, %d need review, %.0f ms",
            statement.id[:8],
            len(statement.transactions),
            len(statement.skipped),
            sum(t.category is Category.NEEDS_REVIEW for t in statement.transactions),
            (time.perf_counter() - started) * 1000,
        )
        return statement

    def get(self, statement_id: str) -> Statement:
        statement = self._store.get(statement_id)
        if statement is None:
            raise NotFoundError("Statement not found. It may have expired; upload it again.")
        return statement

    def fix(self, statement_id: str, txn_id: str, category: Category) -> FixResult:
        with self._store.lock:
            statement = self.get(statement_id)
            txn = next((t for t in statement.transactions if t.id == txn_id), None)
            if txn is None:
                raise NotFoundError("Transaction not found.")

            txn.category = category
            txn.confidence = 1.0
            txn.reason = "You set this category."
            txn.suggestion = None
            txn.user_fixed = True
            txn.related_category = (
                self._brain.related_category(txn.description)
                if category is Category.REFUND
                else None
            )

            # Teach the brain this merchant, then re-run it over the rest of the statement
            # so one fix settles every look-alike row. Rows the user fixed are never touched.
            if self._brain.is_learnable(txn.description) and sign_allows(category, txn.amount):
                statement.learned[self._brain.normalize(txn.description)] = category
            return FixResult(statement, self._recategorize(statement, skip_id=txn.id))

    def _recategorize(self, statement: Statement, *, skip_id: str) -> list[str]:
        changed: list[str] = []
        for txn in statement.transactions:
            if txn.user_fixed or txn.id == skip_id:
                continue
            before = txn.category
            txn.apply(self._brain.categorize(txn.description, txn.amount, statement.learned))
            if txn.category is not before:
                changed.append(txn.id)
        return changed
