import csv
import io
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import from_minor
from app.models import Transaction
from app.services.statements import get_statement

HEADER = [
    "Date",
    "Description",
    "Amount",
    "Currency",
    "Category",
    "Kind",
    "Confidence",
    "Needs Review",
    "Reason",
]


def _safe_cell(text: str) -> str:
    """A spreadsheet runs text that starts with = + - @ as a formula. Prefix those so a
    description in a statement cannot become one."""
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def export_csv(db: Session, statement_id: int) -> tuple[str, str]:
    """Returns (download file name, CSV text). Amounts stay signed; negative = money out."""
    statement = get_statement(db, statement_id)
    transactions = db.scalars(
        select(Transaction)
        .where(Transaction.statement_id == statement_id)
        .order_by(Transaction.row_number)
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(HEADER)
    for t in transactions:
        writer.writerow(
            [
                t.date.isoformat(),
                _safe_cell(t.raw_description),
                str(from_minor(t.amount_minor)),
                t.currency,
                t.category,
                t.kind,
                f"{t.confidence:.2f}",
                "yes" if t.needs_review else "no",
                t.reason,
            ]
        )
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", statement.filename.rsplit(".", 1)[0]) or "statement"
    return f"{stem}-categorized.csv", buffer.getvalue()
