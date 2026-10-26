"""Single authoritative summary for UI and exports; includes reconciliation assertions."""

from .domain import CATEGORIES


def summarize(rows: list[dict]):
    totals = dict.fromkeys(
        [
            "imported_signed_minor",
            "included_signed_minor",
            "excluded_signed_minor",
            "incoming_minor",
            "outgoing_minor",
            "expense_minor",
            "refund_minor",
            "income_minor",
            "transfer_in_minor",
            "transfer_out_minor",
            "personal_in_minor",
            "personal_out_minor",
            "unresolved_in_minor",
            "unresolved_out_minor",
            "excluded_absolute_minor",
        ],
        0,
    )
    counts = dict.fromkeys(
        ["total", "automatic", "reviewed", "needs_review", "duplicate_candidates", "excluded"], 0
    )
    categories = {}
    kind_signed = dict.fromkeys(
        ["expense", "refund", "income", "transfer", "personal", "unresolved"], 0
    )
    for row in rows:
        amount = row["amount_minor"]
        counts["total"] += 1
        totals["imported_signed_minor"] += amount
        if row["duplicate_status"] == "excluded":
            counts["excluded"] += 1
            totals["excluded_signed_minor"] += amount
            totals["excluded_absolute_minor"] += abs(amount)
            continue
        totals["included_signed_minor"] += amount
        totals["incoming_minor" if amount >= 0 else "outgoing_minor"] += abs(amount)
        if row["duplicate_status"] == "pending":
            counts["duplicate_candidates"] += 1
        if row["needs_review"]:
            counts["needs_review"] += 1
        elif row["reviewed"]:
            counts["reviewed"] += 1
        else:
            counts["automatic"] += 1
        # Unconfirmed duplicate candidates remain cash movement, but not trusted expense totals.
        if row["needs_review"]:
            totals["unresolved_in_minor" if amount >= 0 else "unresolved_out_minor"] += abs(amount)
            kind_signed["unresolved"] += amount
            continue
        kind = row["kind"]
        kind_signed[kind] += amount
        if kind in ("expense", "refund"):
            totals["expense_minor" if kind == "expense" else "refund_minor"] += abs(amount)
            item = categories.setdefault(
                row["category"],
                {
                    "category": row["category"],
                    "label": CATEGORIES[row["category"]],
                    "expense_minor": 0,
                    "refund_minor": 0,
                    "net_minor": 0,
                    "count": 0,
                },
            )
            item["expense_minor" if kind == "expense" else "refund_minor"] += abs(amount)
            item["net_minor"] -= amount
            item["count"] += 1
        elif kind == "income":
            totals["income_minor"] += amount
        elif kind in ("transfer", "personal"):
            totals[f"{kind}_{'in' if amount >= 0 else 'out'}_minor"] += abs(amount)
    totals["net_expense_minor"] = totals["expense_minor"] - totals["refund_minor"]
    assert totals["imported_signed_minor"] == (
        totals["included_signed_minor"] + totals["excluded_signed_minor"]
    )
    assert totals["included_signed_minor"] == sum(kind_signed.values())
    assert totals["included_signed_minor"] == totals["incoming_minor"] - totals["outgoing_minor"]
    assert totals["net_expense_minor"] == sum(c["net_minor"] for c in categories.values())
    return {
        "totals": totals,
        "counts": counts,
        "provisional": counts["needs_review"] > 0,
        "categories": sorted(categories.values(), key=lambda c: (-c["net_minor"], c["category"])),
        "kind_signed_minor": kind_signed,
        "reconciled": True,
    }
