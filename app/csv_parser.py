import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.categorizer import CATEGORIES, categorize_transaction

_HEADER_ALIASES = {
    "date": "date",
    "transaction date": "date",
    "posted date": "date",
    "posting date": "date",
    "description": "description",
    "transaction description": "description",
    "transaction details": "description",
    "details": "description",
    "memo": "description",
    "merchant": "description",
    "narrative": "description",
    "amount": "amount",
    "transaction amount": "amount",
    "debit": "debit",
    "debit amount": "debit",
    "withdrawal": "debit",
    "withdrawals": "debit",
    "credit": "credit",
    "credit amount": "credit",
    "deposit": "credit",
    "deposits": "credit",
}
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%Y/%m/%d",
)
_CURRENCY_RE = re.compile(r"[$£€¥]")


class StatementFormatError(ValueError):
    """The CSV file cannot be interpreted as a transaction statement."""


@dataclass
class ParseResult:
    transactions: list[dict[str, Any]]
    invalid_rows: list[dict[str, Any]]
    category_totals: dict[str, float]
    total_rows: int


def _normalize_header(header: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", header.casefold()).split())


def _parse_date(value: str) -> str:
    value = value.strip()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        pass

    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Expected a recognizable transaction date.")


def _parse_amount(value: str) -> Decimal:
    cleaned = _CURRENCY_RE.sub("", value).replace(" ", "").replace("'", "").strip()
    if not cleaned:
        raise ValueError("Amount is required.")

    negative_parentheses = cleaned.startswith("(") and cleaned.endswith(")")
    if negative_parentheses:
        cleaned = cleaned[1:-1]

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            cleaned = ".".join(parts)
        else:
            cleaned = "".join(parts)

    try:
        amount = Decimal(cleaned)
    except InvalidOperation as error:
        raise ValueError("Amount must be a valid number.") from error
    if not amount.is_finite():
        raise ValueError("Amount must be a finite number.")
    if negative_parentheses:
        amount = -abs(amount)
    try:
        return amount.quantize(Decimal("0.01"))
    except InvalidOperation as error:
        raise ValueError("Amount is outside the supported range.") from error


def _raw_row(row: dict[Any, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if key is None:
            result["extra_values"] = value
        else:
            result[str(key)] = value
    return result


def parse_statement(content: bytes) -> ParseResult:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise StatementFormatError("CSV must be encoded as UTF-8.") from error

    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        headers = reader.fieldnames
        if not headers or not any(header and header.strip() for header in headers):
            raise StatementFormatError("CSV is empty or has no header row.")

        canonical_headers: dict[str, str] = {}
        for header in headers:
            if not header or not header.strip():
                continue
            normalized = _normalize_header(header)
            canonical = _HEADER_ALIASES.get(normalized)
            if canonical:
                if canonical in canonical_headers.values():
                    raise StatementFormatError(
                        f"CSV contains multiple columns for '{canonical}'."
                    )
                canonical_headers[header] = canonical

        available = set(canonical_headers.values())
        if "date" not in available or "description" not in available:
            raise StatementFormatError(
                "CSV must include date and description columns."
            )
        if "amount" not in available and not ({"debit", "credit"} & available):
            raise StatementFormatError(
                "CSV must include an amount, debit, or credit column."
            )

        transactions: list[dict[str, Any]] = []
        invalid_rows: list[dict[str, Any]] = []
        totals = {category: Decimal("0.00") for category in CATEGORIES}
        total_rows = 0

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1
            errors: list[str] = []
            raw = _raw_row(row)

            if None in row:
                errors.append("Row has more values than the header.")

            values = {
                canonical: (row.get(header) or "").strip()
                for header, canonical in canonical_headers.items()
            }
            transaction_date = ""
            description = " ".join(values.get("description", "").split())
            amount: Decimal | None = None

            try:
                transaction_date = _parse_date(values.get("date", ""))
            except ValueError as error:
                errors.append(f"date: {error}")

            if not description:
                errors.append("description: Description is required.")

            if values.get("amount") is not None:
                try:
                    amount = _parse_amount(values["amount"])
                except ValueError as error:
                    errors.append(f"amount: {error}")
            else:
                debit = values.get("debit", "")
                credit = values.get("credit", "")
                if debit and credit:
                    errors.append(
                        "amount: Provide either a debit or credit, not both."
                    )
                elif not debit and not credit:
                    errors.append("amount: Debit or credit is required.")
                else:
                    field = "debit" if debit else "credit"
                    try:
                        amount = _parse_amount(debit or credit)
                        if field == "debit":
                            amount = -abs(amount)
                        else:
                            amount = abs(amount)
                    except ValueError as error:
                        errors.append(f"{field}: {error}")

            if errors:
                invalid_rows.append(
                    {"row_number": row_number, "errors": errors, "row_data": raw}
                )
                continue

            if amount is None:
                invalid_rows.append(
                    {
                        "row_number": row_number,
                        "errors": ["amount: Amount is required."],
                        "row_data": raw,
                    }
                )
                continue
            category, transaction_type, needs_review, review_reason = (
                categorize_transaction(description, amount)
            )
            transaction = {
                "row_number": row_number,
                "date": transaction_date,
                "description": description,
                "amount": float(amount),
                "category": category,
                "transaction_type": transaction_type,
                "needs_review": needs_review,
                "review_reason": review_reason,
            }
            transactions.append(transaction)
            totals[category] += amount

    except csv.Error as error:
        raise StatementFormatError(f"Could not read CSV: {error}") from error

    return ParseResult(
        transactions=transactions,
        invalid_rows=invalid_rows,
        category_totals={
            category: float(total.quantize(Decimal("0.01")))
            for category, total in totals.items()
        },
        total_rows=total_rows,
    )
