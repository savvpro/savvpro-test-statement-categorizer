from collections import defaultdict
from decimal import Decimal

from .brain.classifier import classify
from .parser import parse_statement

CENT = Decimal("0.01")


def compute_totals(rows) -> dict:
    sums = defaultdict(lambda: Decimal("0"))
    for row in rows:
        sums[row["category"]] += Decimal(row["amount"])
    return {cat: str(v.quantize(CENT)) for cat, v in sorted(sums.items())}


def categorize_statement(content: bytes) -> dict:
    rows, errors = parse_statement(content)
    seen, out = set(), []
    for i, row in enumerate(rows):
        verdict = classify(row["description"], row["amount"])
        key = (row["date"], row["description"].upper(), row["amount"])
        out.append({
            "id": i,
            "line": row["line"],
            "date": row["date"],
            "description": row["description"],
            "amount": str(row["amount"].quantize(CENT)),
            "category": verdict.category,
            "reason": verdict.reason,
            "needs_review": verdict.needs_review,
            # flagged, not dropped: two identical coffees can be real
            "possible_duplicate": key in seen,
        })
        seen.add(key)
    return {"rows": out, "errors": errors, "totals": compute_totals(out)}
