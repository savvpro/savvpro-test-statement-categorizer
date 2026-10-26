"""CSV export of a categorized statement."""

import csv
import io

from app.brain.taxonomy import get_category
from app.db.models import Statement
from app.db.money import format_amount

HEADER = [
    "date",
    "description",
    "amount",
    "category",
    "schedule_c_line",
    "status",
    "confidence",
    "reasons",
]
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe(text: str) -> str:
    """Stop spreadsheet apps from running a description as a formula (CSV injection)."""
    return f"'{text}" if text.startswith(_FORMULA_PREFIXES) else text


def export_csv(statement: Statement) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for txn in statement.transactions:
        category = get_category(txn.category_id)
        writer.writerow(
            [
                txn.date.isoformat(),
                _safe(txn.description_raw),
                format_amount(txn.amount),
                category.label,
                category.schedule_c_line or "",
                txn.status.value,
                f"{txn.confidence:.2f}",
                _safe("; ".join(txn.reasons)),
            ]
        )
    return buffer.getvalue()
