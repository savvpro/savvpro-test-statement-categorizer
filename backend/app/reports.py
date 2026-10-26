"""Integer minor-unit accounting. Unknown purpose never enters business totals."""

from decimal import ROUND_HALF_UP, Decimal


def summarize(rows: list[dict]) -> dict:
    currencies = {}
    for row in rows:
        currency = row["currency"]
        totals = currencies.setdefault(
            currency,
            {
                "money_out": 0,
                "money_in": 0,
                "net_movement": 0,
                "gross_expenses": 0,
                "refunds": 0,
                "net_expenses": 0,
                "business": 0,
                "personal": 0,
                "unallocated": 0,
                "excluded": 0,
                "income": 0,
                "unresolved_credits": 0,
                "categories": {},
            },
        )
        amount = row["amount_minor"]
        totals["money_out"] += max(amount, 0)
        totals["money_in"] += max(-amount, 0)
        totals["net_movement"] += amount
        if row["kind"] in {"expense", "refund"}:
            if row["kind"] == "expense":
                totals["gross_expenses"] += amount
            else:
                totals["refunds"] += -amount
            totals["net_expenses"] += amount
            totals["categories"][row["category"]] = totals["categories"].get(row["category"], 0) + amount
            if row["purpose"] in {"business", "mixed"} and not row["needs_review"]:
                business = int(
                    (Decimal(amount) * Decimal(row["business_percent"]) / 100).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                )
                totals["business"] += business
                totals["personal"] += amount - business
            elif row["purpose"] == "personal" and not row["needs_review"]:
                totals["personal"] += amount
            else:
                totals["unallocated"] += amount
        elif row["kind"] == "income":
            totals["income"] += -amount
        elif row["kind"] == "unresolved":
            totals["unresolved_credits"] += amount
        else:
            totals["excluded"] += abs(amount)
    return {
        "currencies": currencies,
        "total_rows": len(rows),
        "needs_review": sum(bool(row["needs_review"]) for row in rows),
        "confirmed": sum(row.get("review_status") == "confirmed" for row in rows),
    }
