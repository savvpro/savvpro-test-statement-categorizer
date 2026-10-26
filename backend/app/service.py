"""Glue: parsed rows -> categorized rows -> summary."""
from collections import Counter
from decimal import Decimal
from typing import Dict, List

from . import rules
from .categorizer import categorize, normalize
from .parser import ParseResult


def build_rows(parsed: ParseResult) -> List[Dict]:
    seen = Counter((r.date, r.amount, normalize(r.description)) for r in parsed.rows)
    rows = []
    for r in parsed.rows:
        result = categorize(r.description, r.amount)
        key = (r.date, r.amount, normalize(r.description))
        rows.append({
            "id": r.row_number,
            "date": r.date,
            "description": r.description,
            "merchant": normalize(r.description),
            "amount": float(r.amount),
            "category": result.category,
            "status": result.status,
            "reason": result.reason,
            "refund_of": result.refund_of,
            "possible_duplicate": seen[key] > 1,
        })
    return rows


def summarize(rows: List[Dict]) -> Dict:
    """Totals per category. Refunds reduce the category they came from."""
    totals = {c: Decimal(0) for c in rules.SPENDING_CATEGORIES}
    refunds = not_spending = Decimal(0)
    review_count = 0
    for row in rows:
        amount = Decimal(str(row["amount"]))
        category = row["category"]
        if category == rules.NEEDS_REVIEW:
            review_count += 1
        elif category == rules.NOT_SPENDING:
            not_spending += abs(amount)
        elif category == rules.REFUND:
            refunds += amount
            if row.get("refund_of") in totals:
                totals[row["refund_of"]] -= amount
        elif category in totals:
            totals[category] += -amount
    return {
        "by_category": {c: float(v) for c, v in totals.items()},
        "total_spending": float(sum(totals.values())),
        "refunds": float(refunds),
        "not_spending": float(not_spending),
        "needs_review_count": review_count,
        "row_count": len(rows),
    }
