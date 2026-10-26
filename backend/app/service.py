"""Application service: upload -> parse -> brain -> stored statement; review; totals."""
from __future__ import annotations

import threading
import uuid
from decimal import Decimal

from .brain import Brain
from .models import NON_TAX_CATEGORIES, Category, Kind, Transaction
from .parser import parse_csv


class NotFound(LookupError):
    pass


def _suggested(flags: list[str]) -> Category | None:
    for f in flags:
        if f.startswith("suggest:"):
            return Category(f.split(":", 1)[1])
    return None


class StatementService:
    """In-memory store. Swap for a database in production; the interface stays."""

    def __init__(self, brain: Brain | None = None):
        self.brain = brain or Brain()
        self._statements: dict[str, dict] = {}
        self._lock = threading.Lock()

    def upload(self, filename: str, content: bytes) -> dict:
        parsed = parse_csv(content)
        txs: list[Transaction] = []
        for raw, merchant, d in self.brain.categorise(parsed.transactions):
            txs.append(Transaction(
                id=uuid.uuid4().hex[:12], row_number=raw.row_number, date=raw.date,
                description=raw.description, merchant=merchant, amount=raw.amount, kind=raw.kind,
                category=d.category, suggested_category=_suggested(d.flags),
                confidence=round(d.confidence, 2), reason=d.reason, is_refund=d.is_refund,
                flags=[f for f in d.flags if not f.startswith("suggest:")],
            ))
        sid = uuid.uuid4().hex[:12]
        with self._lock:
            self._statements[sid] = {"id": sid, "filename": filename, "transactions": txs, "errors": parsed.errors}
        return self.view(sid)

    def view(self, sid: str) -> dict:
        st = self._get(sid)
        txs = st["transactions"]
        return {
            "id": sid,
            "filename": st["filename"],
            "transactions": [t.to_dict() for t in txs],
            "errors": st["errors"],
            "summary": summarise(txs),
        }

    def review(self, sid: str, tx_id: str, category: Category, apply_to_same_merchant: bool = True) -> dict:
        st = self._get(sid)
        target = next((t for t in st["transactions"] if t.id == tx_id), None)
        if target is None:
            raise NotFound(f"transaction {tx_id} not found")
        with self._lock:
            target.category, target.user_overridden = category, True
            if not target.is_refund:
                self.brain.learn(target.merchant, category)
            if apply_to_same_merchant:
                from .brain import merchant_key
                key = merchant_key(target.merchant)
                for t in st["transactions"]:
                    if (t is not target and t.category == Category.NEEDS_REVIEW and not t.is_refund
                            and t.kind == target.kind and merchant_key(t.merchant) == key):
                        t.category, t.user_overridden = category, True
                        t.reason = f"Applied your choice for '{key}'."
        return self.view(sid)

    def _get(self, sid: str) -> dict:
        st = self._statements.get(sid)
        if st is None:
            raise NotFound(f"statement {sid} not found")
        return st


def summarise(txs: list[Transaction]) -> dict:
    """Tax totals. Refunds reduce their category. Transfers/card payments/personal excluded."""
    totals: dict[str, Decimal] = {}
    expenses = income = Decimal(0)
    needs_review = 0
    for t in txs:
        if t.category == Category.NEEDS_REVIEW:
            needs_review += 1
            continue
        if t.category in NON_TAX_CATEGORIES:
            continue
        signed = t.amount if t.kind == Kind.DEBIT else -t.amount  # refund reduces spend
        if t.category == Category.CLIENT_INCOME:
            income += t.amount
            totals[t.category.value] = totals.get(t.category.value, Decimal(0)) + t.amount
            continue
        totals[t.category.value] = totals.get(t.category.value, Decimal(0)) + signed
        expenses += signed
    return {
        "by_category": {k: str(v.quantize(Decimal("0.01"))) for k, v in sorted(totals.items())},
        "total_expenses": str(expenses.quantize(Decimal("0.01"))),
        "total_income": str(income.quantize(Decimal("0.01"))),
        "needs_review": needs_review,
        "ready_for_tax": needs_review == 0,
    }
