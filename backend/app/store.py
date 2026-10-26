"""In-memory statement storage.

Good enough for a single-process demo and trivially replaceable: the service only uses
`add` and `get`. The next step for production is a database (see DESIGN.md).
"""

import threading
from collections import OrderedDict

from .models import Statement


class StatementStore:
    def __init__(self, max_statements: int = 200) -> None:
        self._items: OrderedDict[str, Statement] = OrderedDict()
        self._max = max_statements
        self.lock = threading.RLock()  # held by the service around read-modify-write

    def add(self, statement: Statement) -> None:
        with self.lock:
            self._items[statement.id] = statement
            while len(self._items) > self._max:
                self._items.popitem(last=False)  # drop the oldest

    def get(self, statement_id: str) -> Statement | None:
        with self.lock:
            return self._items.get(statement_id)

    def __len__(self) -> int:
        return len(self._items)
