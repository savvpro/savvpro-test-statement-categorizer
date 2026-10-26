import csv
import io

from app.config import BASE_CURRENCY
from app.parser.normalizer import normalize_description, parse_amount, parse_date
from app.schemas import SkippedRow, Transaction

REQUIRED_COLUMNS = {"date", "description", "amount"}


class ParseError(ValueError):
    """Poori file kharab hai (khali, columns missing, wagera)."""


def parse_csv(content: bytes) -> tuple[list[Transaction], list[SkippedRow]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ParseError("File must be a UTF-8 text CSV") from None
    if not text.strip():
        raise ParseError("File is empty")

    reader = csv.DictReader(io.StringIO(text))
    headers = {h.strip().lower() for h in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise ParseError(f"Missing columns: {', '.join(sorted(missing))}")

    transactions: list[Transaction] = []
    skipped: list[SkippedRow] = []

    for line_no, raw_row in enumerate(reader, start=2):  # line 1 = header
        row = {
            k.strip().lower(): (v or "").strip()
            for k, v in raw_row.items()
            if k is not None and isinstance(v, (str, type(None)))
        }
        try:
            if not row.get("description"):
                raise ValueError("empty description")
            transactions.append(
                Transaction(
                    id=f"row-{line_no}",
                    row=line_no,
                    date=parse_date(row["date"]),
                    raw_description=row["description"],
                    description=normalize_description(row["description"]),
                    amount=parse_amount(row["amount"]),
                    currency=(row.get("currency") or BASE_CURRENCY).upper(),
                )
            )
        except ValueError as exc:
            skipped.append(SkippedRow(row=line_no, reason=str(exc)))

    return transactions, skipped