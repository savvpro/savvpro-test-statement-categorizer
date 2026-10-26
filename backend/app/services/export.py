"""CSV export of a categorised statement, ready to hand to an accountant."""

import csv
import io

from ..models import Statement

# A cell starting with one of these is run as a formula by Excel/Sheets. Bank
# descriptions are untrusted text, so neutralise them (CSV injection).
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe(text: str) -> str:
    return f"'{text}" if text.startswith(_FORMULA_PREFIXES) else text


def statement_to_csv(statement: Statement) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(
        ["Date", "Description", "Amount", "Category", "Confidence %", "Why", "Fixed by you"]
    )
    for t in statement.transactions:
        writer.writerow(
            [
                t.date.isoformat(),
                _safe(t.description),
                f"{t.amount:.2f}",
                t.category.value,
                round(t.confidence * 100),
                _safe(t.reason),
                "yes" if t.user_fixed else "",
            ]
        )
    return buffer.getvalue().encode("utf-8-sig")  # BOM so Excel opens it as UTF-8
