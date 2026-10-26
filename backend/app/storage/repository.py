"""Where finished statements live.

An in-memory store keeps the app dependency-free for local use and for the assessment.
The Protocol is the seam: swap in a database-backed class without touching the services.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Protocol

from app.domain.models import Statement


class StatementRepository(Protocol):
    def save(self, statement: Statement) -> None: ...

    def get(self, statement_id: str) -> Statement | None: ...


class InMemoryStatementRepository:
    """Thread-safe store that evicts the oldest statements beyond a fixed capacity."""

    def __init__(self, capacity: int = 200):
        self._capacity = capacity
        self._items: OrderedDict[str, Statement] = OrderedDict()
        self._lock = threading.Lock()

    def save(self, statement: Statement) -> None:
        with self._lock:
            self._items[statement.id] = statement
            self._items.move_to_end(statement.id)
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)

    def get(self, statement_id: str) -> Statement | None:
        with self._lock:
            return self._items.get(statement_id)
