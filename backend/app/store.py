from .schemas import Transaction

# ponytail: one module-level statement, no locking; swap for per-session storage if multi-user.
_transactions: list[Transaction] = []


def replace(transactions: list[Transaction]) -> None:
    _transactions[:] = transactions


def all_transactions() -> list[Transaction]:
    return list(_transactions)


def get(tx_id: int) -> Transaction | None:
    return next((t for t in _transactions if t.id == tx_id), None)
