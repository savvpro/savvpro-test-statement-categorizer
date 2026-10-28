"""Statement-level logic on top of the per-row brain.

Some decisions need the whole statement, not one row:
- the same charge twice on the same day is a possible duplicate,
- a pending charge can still change or vanish,
- a refund should reduce the category of the purchase it reverses.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.brain import categorize
from app.domain.categories import CATEGORIES, NEEDS_REVIEW, Kind, is_deductible, kind_of
from app.ingest.normalize import merchant_key
from app.ingest.parsing import RawTransaction


def categorize_statement(rows: list[RawTransaction], learned: dict[str, str]) -> list[dict]:
    out: list[dict] = []
    seen: dict[tuple, int] = {}
    for raw in rows:
        decision = categorize(raw.description, raw.amount, learned)
        item = {
            "row": raw.row,
            "date": raw.date.isoformat(),
            "description": raw.description,
            "merchant": merchant_key(raw.description),
            "amount": str(raw.amount),
            "category": decision.category,
            "confidence": round(decision.confidence, 2),
            "reason": decision.reason,
            "rule": decision.rule,
            "suggestion": decision.suggestion,
            "pending": raw.pending,
            "refund_of": None,
        }
        dup_key = (raw.date, raw.description.upper(), raw.amount)
        if dup_key in seen:
            item |= _to_review(item, f"Possible duplicate of row {seen[dup_key]}", "duplicate")
        else:
            seen[dup_key] = raw.row
        if raw.pending and item["category"] != NEEDS_REVIEW:
            item |= _to_review(item, "Pending charge: it may change or disappear", "pending")
        out.append(item)
    link_refunds(out)
    return out


def _to_review(item: dict, reason: str, rule: str) -> dict:
    return {
        "category": NEEDS_REVIEW,
        "suggestion": item["category"] if item["category"] != NEEDS_REVIEW else item["suggestion"],
        "reason": reason,
        "rule": rule,
        "confidence": min(item["confidence"], 0.5),
    }


def link_refunds(items: list[dict]) -> None:
    """Point each refund at the expense category it reverses (same merchant)."""
    spent_at: dict[str, str] = {}
    for it in items:
        if kind_of(it["category"]) == Kind.EXPENSE:
            spent_at.setdefault(it["merchant"], it["category"])
    for it in items:
        it["refund_of"] = spent_at.get(it["merchant"]) if it["category"] == "Refund" else None


def summarize(items: list[dict]) -> dict:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for it in items:
        amount = Decimal(it["amount"])
        totals[it["category"]] += abs(amount)
        if it["category"] == "Refund" and it["refund_of"]:
            # Shown under Refund for visibility, and subtracted from the
            # purchase category. Refund is not income or a deductible, so it
            # is never counted twice in the headline totals.
            totals[it["refund_of"]] -= amount
    by_category = [
        {
            "category": name,
            "kind": kind_of(name).value,
            "deductible": is_deductible(name),
            "total": f"{totals[name]:.2f}",
            "count": sum(1 for it in items if it["category"] == name),
        }
        for name in CATEGORIES
        if any(it["category"] == name or it["refund_of"] == name for it in items)
    ]

    def total(pred) -> str:
        return f"{sum((v for k, v in totals.items() if pred(k)), Decimal(0)):.2f}"

    return {
        "income": total(lambda c: kind_of(c) == Kind.INCOME),
        "deductible_expenses": total(is_deductible),
        "personal_spending": total(lambda c: kind_of(c) == Kind.EXPENSE and not is_deductible(c)),
        "not_spending": total(lambda c: kind_of(c) == Kind.NOT_SPENDING),
        "unlinked_refunds": f"{sum((Decimal(i['amount']) for i in items if i['category'] == 'Refund' and not i['refund_of']), Decimal(0)):.2f}",
        "needs_review": sum(1 for it in items if it["category"] == NEEDS_REVIEW),
        "transactions": len(items),
        "by_category": by_category,
    }
