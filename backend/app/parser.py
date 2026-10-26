import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .normalizer import has_usd, normalize
from .schemas import Transaction

DATE_FORMAT = "%d-%m-%Y"
REQUIRED = ("date", "description", "debit", "credit", "balance")


@dataclass
class ParseResult:
    transactions: list[Transaction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _money(cell: str | None) -> Decimal | None:
    """Empty cell -> None. Thousands separators allowed. Bad or non-finite -> ValueError."""
    cell = (cell or "").replace(",", "").strip()
    if not cell:
        return None
    try:
        value = Decimal(cell)
    except InvalidOperation:
        raise ValueError(f"invalid number {cell!r}") from None
    if not value.is_finite():
        raise ValueError(f"invalid number {cell!r}")
    return value


def _signed_amount(debit: Decimal | None, credit: Decimal | None) -> Decimal:
    if (debit is None) == (credit is None):
        raise ValueError("exactly one of Debit or Credit is required")
    amount = credit if debit is None else -debit
    if amount == 0 or (debit is not None and debit < 0) or (credit is not None and credit < 0):
        raise ValueError("amount must be positive")
    return amount


def parse_csv(text: str) -> ParseResult:
    """Parse a statement. Bad rows are reported in `errors`, never raised."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    reader.fieldnames = [(name or "").strip().lower() for name in reader.fieldnames or []]
    missing = [name for name in REQUIRED if name not in reader.fieldnames]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    result = ParseResult()
    for row in reader:
        line = reader.line_num
        if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
            continue
        try:
            description = " ".join((row["description"] or "").split())
            if not description:
                raise ValueError("empty description")
            tx_date = datetime.strptime((row["date"] or "").strip(), DATE_FORMAT).date()
            amount = _signed_amount(_money(row["debit"]), _money(row["credit"]))
            balance = _money(row["balance"])
        except ValueError as exc:
            result.errors.append(f"line {line}: {exc}")
            continue
        result.transactions.append(
            Transaction(
                id=len(result.transactions) + 1,
                date=tx_date,
                description=description,
                normalized=normalize(description),
                amount=amount,
                balance=balance,
                usd_hint=has_usd(description),
            )
        )
    return result
