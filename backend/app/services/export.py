"""CSV export with formula-injection escaping."""

import csv
import io
from collections.abc import Iterable

from app.core.security import csv_escape
from app.db.models import TransactionRow
from app.domain.enums import Category
from app.domain.taxonomy import TAXONOMY
from app.ingest.amounts import format_cents

COLUMNS = (
    "date",
    "description",
    "amount",
    "category",
    "category_label",
    "schedule_e_line",
    "status",
    "confidence",
    "flags",
    "reasons",
)


def export_csv(rows: Iterable[TransactionRow]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for r in rows:
        info = TAXONOMY[Category(r.category)] if r.category else None
        writer.writerow(
            [
                r.posted_date.isoformat(),
                csv_escape(r.description),
                format_cents(r.amount_cents),  # our own formatting, never user text
                csv_escape(r.category or ""),
                csv_escape(info.label if info else ""),
                csv_escape(info.schedule_e_line or "" if info else ""),
                csv_escape(r.status),
                f"{r.confidence:.2f}",
                csv_escape(";".join(r.flags)),
                csv_escape(" | ".join(r.reasons)),
            ]
        )
    return buf.getvalue()
