"""Exact accounting summaries and spreadsheet-safe CSV exports."""

import csv
import io
from decimal import Decimal

from .domain import EXPENSE_CATEGORIES


def summarize(transactions: list[dict]) -> dict:
    """Unresolved/excluded rows never contribute to accepted financial totals."""
    categories = {
        str(category): {"category": str(category), "spent_minor": 0, "refund_minor": 0, "net_minor": 0, "count": 0}
        for category in sorted(EXPENSE_CATEGORIES)
    }
    result = {
        "transaction_count": len(transactions),
        "review_count": 0,
        "auto_count": 0,
        "reviewed_count": 0,
        "excluded_count": 0,
        "spent_minor": 0,
        "refund_minor": 0,
        "net_expenses_minor": 0,
        "income_minor": 0,
        "transfer_in_minor": 0,
        "transfer_out_minor": 0,
        "raw_net_minor": 0,
        "accepted_net_minor": 0,
        "unresolved_net_minor": 0,
        "excluded_net_minor": 0,
        "unresolved_in_minor": 0,
        "unresolved_out_minor": 0,
    }
    for row in transactions:
        amount = row["amount_minor"]
        result["raw_net_minor"] += amount
        if row["excluded"]:
            result["excluded_count"] += 1
            result["excluded_net_minor"] += amount
            continue
        if row["status"] == "needs_review":
            result["review_count"] += 1
            result["unresolved_net_minor"] += amount
            result["unresolved_in_minor" if amount > 0 else "unresolved_out_minor"] += abs(amount)
            continue
        result["auto_count" if row["status"] == "auto" else "reviewed_count"] += 1
        result["accepted_net_minor"] += amount
        kind = row["kind"]
        if kind in ("expense", "refund"):
            key = "spent_minor" if kind == "expense" else "refund_minor"
            result[key] += abs(amount)
            categories[row["category"]][key] += abs(amount)
            categories[row["category"]]["count"] += 1
        elif kind == "income":
            result["income_minor"] += amount
        elif kind == "transfer":
            result["transfer_in_minor" if amount > 0 else "transfer_out_minor"] += abs(amount)
    result["net_expenses_minor"] = result["spent_minor"] - result["refund_minor"]
    for category in categories.values():
        category["net_minor"] = category["spent_minor"] - category["refund_minor"]
    result["categories"] = list(categories.values())
    return result


def money_text(minor: int) -> str:
    return f"{Decimal(minor) / 100:.2f}"


def safe_text(value: str) -> str:
    # Quoting alone does not prevent spreadsheet formula injection. Prefix text cells.
    return (
        "'" + value
        if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))
        else value
    )


def export_transactions(statement: dict) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "source_row",
            "date",
            "description",
            "amount",
            "currency",
            "category",
            "kind",
            "status",
            "excluded",
            "rule_strength",
            "rule_id",
            "machine_reason",
            "review_flags",
            "review_note",
            "version",
        ]
    )
    for row in statement["transactions"]:
        writer.writerow(
            [
                row["source_row"],
                row["date"],
                safe_text(row["description"]),
                money_text(row["amount_minor"]),
                row["currency"],
                row["category"],
                row["kind"],
                row["status"],
                row["excluded"],
                row["confidence"],
                row["rule_id"],
                safe_text(row["reason"]),
                "; ".join(row["review_flags"]),
                safe_text(row["note"]),
                row["version"],
            ]
        )
    return output.getvalue()


def export_summary(statement: dict) -> str:
    summary = summarize(statement["transactions"])
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        ["category", "money_out", "money_in", "net_expenses", "currency", "accepted_rows", "unresolved_rows"]
    )
    for category in summary["categories"]:
        writer.writerow(
            [
                category["category"],
                money_text(category["spent_minor"]),
                money_text(category["refund_minor"]),
                money_text(category["net_minor"]),
                statement["currency"],
                category["count"],
                summary["review_count"],
            ]
        )
    # Non-expense categories remain visible to an accountant without inflating spending.
    for category in ("Income", "Transfers", "Personal"):
        rows = [
            row
            for row in statement["transactions"]
            if row["category"] == category and row["status"] != "needs_review" and not row["excluded"]
        ]
        money_out = -sum(min(0, row["amount_minor"]) for row in rows)
        money_in = sum(max(0, row["amount_minor"]) for row in rows)
        writer.writerow(
            [
                category,
                money_text(money_out),
                money_text(money_in),
                "0.00",
                statement["currency"],
                len(rows),
                summary["review_count"],
            ]
        )
    return output.getvalue()
