"""Business constraints, derived totals, and safe CSV presentation."""

import csv
import io
from decimal import Decimal

from backend.app.engine import EXPENSE_CATEGORIES
from backend.app.parser import StatementError


def validate_review(amount_cents: int, category: str, kind: str) -> None:
    allowed = {
        "expense": EXPENSE_CATEGORIES,
        "refund": EXPENSE_CATEGORIES,
        "income": ("Client income",),
        "transfer": ("Transfer",),
        "personal": ("Personal",),
        "excluded": ("Excluded",),
    }
    if category not in allowed.get(kind, ()):
        raise StatementError("Choose a category that matches the transaction type.")
    if kind == "expense" and amount_cents > 0:
        raise StatementError("Incoming money cannot be an expense. Choose refund or income.")
    if kind in ("refund", "income") and amount_cents < 0:
        raise StatementError("Outgoing money cannot be income or a refund.")


def add_summary(statement: dict) -> dict:
    rows = statement["transactions"]
    summary = {
        "transaction_count": len(rows),
        "needs_review": 0,
        "reviewed": 0,
        "net_expenses_cents": 0,
        "income_cents": 0,
        "refunds_cents": 0,
        "pending_outflow_cents": 0,
        "pending_inflow_cents": 0,
        "excluded_count": 0,
        "categories": {},
    }
    for row in rows:
        amount = row["amount_cents"]
        if row["status"] == "needs_review":
            summary["needs_review"] += 1
            key = "pending_outflow_cents" if amount < 0 else "pending_inflow_cents"
            summary[key] += abs(amount)
            continue
        if row["status"] == "reviewed":
            summary["reviewed"] += 1
        if row["kind"] in ("expense", "refund"):
            summary["net_expenses_cents"] -= amount
            category = row["category"]
            summary["categories"][category] = summary["categories"].get(category, 0) - amount
            if row["kind"] == "refund":
                summary["refunds_cents"] += amount
        elif row["kind"] == "income":
            summary["income_cents"] += amount
        else:
            summary["excluded_count"] += 1
    statement["summary"] = summary
    statement["date_from"] = min(row["date"] for row in rows)
    statement["date_to"] = max(row["date"] for row in rows)
    return statement


def safe_cell(value: object) -> str:
    text = str(value or "")
    # Prefix untrusted text that spreadsheet programs could interpret as formulas.
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def export_csv(statement: dict) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "transaction_id",
            "date",
            "description",
            "amount",
            "currency",
            "category",
            "kind",
            "status",
            "reason",
            "note",
            "source_row",
        ]
    )
    for row in statement["transactions"]:
        writer.writerow(
            [
                safe_cell(row["source_id"]),
                row["date"],
                safe_cell(row["description"]),
                f"{Decimal(row['amount_cents']) / 100:.2f}",
                statement["currency"],
                row["category"] or "Needs Review",
                row["kind"],
                row["status"],
                safe_cell(row["reason"]),
                safe_cell(row["note"]),
                row["row_number"],
            ]
        )
    return output.getvalue().encode("utf-8-sig")
