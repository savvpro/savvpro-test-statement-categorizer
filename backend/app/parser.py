import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from .models import Transaction


def _field(row: dict[str, str], *names: str) -> str:
    normalized = {key.strip().lower(): value.strip() for key, value in row.items() if key}
    for name in names:
        if normalized.get(name):
            return normalized[name]
    return ""


def parse_csv(content: bytes) -> list[Transaction]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("The statement must be a UTF-8 CSV file.") from error
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("The CSV must include a header row.")

    transactions: list[Transaction] = []
    for line_number, row in enumerate(reader, start=2):
        raw_date = _field(row, "date", "transaction date")
        merchant = _field(row, "merchant", "payee")
        details = _field(row, "description", "details", "memo")
        description = " - ".join(part for part in (merchant, details) if part)
        raw_amount = _field(row, "amount", "total")
        raw_type = _field(row, "type", "direction")
        if not raw_date and not description and not raw_amount:
            continue
        try:
            parsed_date = date.fromisoformat(raw_date) if raw_date else None
            amount = Decimal(raw_amount.replace(",", "").replace("$", "").strip())
        except (ValueError, InvalidOperation) as error:
            raise ValueError(f"Invalid date or amount on CSV line {line_number}.") from error
        if not description:
            raise ValueError(f"Missing description on CSV line {line_number}.")
        direction = (
            "income"
            if raw_type.lower() in {"income", "credit", "deposit"}
            or (not raw_type and raw_date and amount > 0)
            else "expense"
        )
        transactions.append(
            Transaction(
                id=str(uuid4()),
                date=parsed_date,
                description=description,
                amount=abs(amount),
                currency=_field(row, "currency") or "USD",
                direction=direction,
            )
        )
    if not transactions:
        raise ValueError("The statement has no readable transactions.")
    return transactions
