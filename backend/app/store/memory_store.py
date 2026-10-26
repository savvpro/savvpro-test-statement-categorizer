import uuid
from app.brain.models import Transaction, Decision

_store: dict[str, dict] = {}

def save_batch(rows: list[tuple[Transaction, Decision]]) -> list[dict]:
    out = []
    for tx, d in rows:
        rid = str(uuid.uuid4())
        record = {
            "id": rid,
            "date": tx.date.isoformat(),
            "description": tx.description,
            "amount": str(tx.amount),
            "category": d.category.value,
            "confidence": d.confidence,
            "reason": d.reason,
        }
        _store[rid] = record
        out.append(record)
    return out

def update_row(rid: str, category: str) -> dict | None:
    if rid not in _store:
        return None
    _store[rid]["category"] = category
    _store[rid]["confidence"] = 1.0
    _store[rid]["reason"] = "User override"
    return _store[rid]