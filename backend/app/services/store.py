from app.schemas import Transaction


class StatementStore:
    """In-memory store: aik waqt mai aik statement. Kal DB lagana ho to sirf yeh file badlo."""

    def __init__(self) -> None:
        self._items: dict[str, Transaction] = {}

    def replace(self, transactions: list[Transaction]) -> None:
        self._items = {t.id: t for t in transactions}

    def get(self, txn_id: str) -> Transaction | None:
        return self._items.get(txn_id)

    def all(self) -> list[Transaction]:
        return list(self._items.values())


_store = StatementStore()


def get_store() -> StatementStore:
    return _store