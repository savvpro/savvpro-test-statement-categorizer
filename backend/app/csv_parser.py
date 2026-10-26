import csv
import io
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

MAX_FILE_BYTES = 1024 * 1024
MAX_TRANSACTIONS = 5000
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y")
HEADER_ALIASES = {
    "date": {"date", "transaction date", "booking date"},
    "description": {"description", "details", "narrative", "transaction description"},
    "amount": {"amount", "transaction amount"},
    "debit": {"debit", "debit amount", "money out"},
    "credit": {"credit", "credit amount", "money in"},
    "transaction_type": {"type", "transaction type"},
    "currency": {"currency", "currency code"},
}


class CSVValidationError(ValueError):
    pass


@dataclass
class ParsedTransaction:
    row_number: int
    date: str
    description: str
    amount: Decimal
    transaction_type: str
    possible_duplicate: bool = False


def normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def parse_money(value: str) -> Decimal:
    value = value.strip()
    if not re.fullmatch(r"[+-]?\d{1,10}(?:\.\d{1,2})?", value):
        raise CSVValidationError(
            "amounts must use a decimal point and at most two decimal places, without currency symbols or thousands separators"
        )
    amount = Decimal(value).quantize(Decimal("0.01"))
    return amount if amount else Decimal("0.00")


def parse_date(value: str) -> str:
    value = value.strip()
    for date_format in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, date_format)
            if parsed.strftime(date_format) == value:
                return parsed.date().isoformat()
        except ValueError:
            continue
    raise CSVValidationError("date must be YYYY-MM-DD, DD/MM/YYYY, or DD.MM.YYYY")


def parse_csv(content: bytes) -> list[ParsedTransaction]:
    if len(content) > MAX_FILE_BYTES:
        raise CSVValidationError("CSV files must be 1 MiB or smaller.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CSVValidationError("Use a UTF-8 encoded CSV file.") from None
    if not text.strip():
        raise CSVValidationError(
            "The file is empty. Include a header and at least one transaction."
        )
    if "\x00" in text:
        raise CSVValidationError("The file contains unsupported null characters.")

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = next(reader)
        columns: dict[str, int] = {}
        normalized = [normalize_header(header) for header in headers]
        if len(set(normalized)) != len(normalized) or "" in normalized:
            raise CSVValidationError("Column headers must be nonempty and unique.")
        for name, aliases in HEADER_ALIASES.items():
            matches = [
                index for index, header in enumerate(normalized) if header in aliases
            ]
            if len(matches) > 1:
                raise CSVValidationError(
                    f"More than one column maps to {name}. Keep only one."
                )
            if matches:
                columns[name] = matches[0]
        if not {"date", "description"} <= columns.keys():
            raise CSVValidationError(
                "Include Date and Description columns. Use comma-separated CSV."
            )
        has_amount = "amount" in columns
        has_split = "debit" in columns and "credit" in columns
        if has_amount and ("debit" in columns or "credit" in columns):
            raise CSVValidationError(
                "Use Amount or Debit and Credit, not both formats."
            )
        if not has_amount and not has_split:
            raise CSVValidationError(
                "Include a signed Amount column or both Debit and Credit columns."
            )

        transactions = []
        errors = []
        error_count = 0
        for row in reader:
            row_number = reader.line_num
            if len(transactions) + error_count >= MAX_TRANSACTIONS:
                raise CSVValidationError(
                    f"A statement can contain at most {MAX_TRANSACTIONS:,} transactions."
                )
            try:
                if len(row) != len(headers):
                    raise CSVValidationError(
                        "column count does not match the header; blank rows are not transactions"
                    )

                values = {name: row[index].strip() for name, index in columns.items()}
                date = parse_date(values["date"])
                description = values["description"]
                if not description or len(description) > 500:
                    raise CSVValidationError(
                        "description must contain 1 to 500 characters"
                    )
                if any(ord(character) < 32 for character in description):
                    raise CSVValidationError(
                        "description must not contain control characters"
                    )
                if "currency" in columns and values["currency"].upper() != "PKR":
                    raise CSVValidationError(
                        "currency must be PKR; currency conversion is not supported"
                    )
                transaction_type = values.get("transaction_type", "")
                if len(transaction_type) > 80 or any(
                    ord(char) < 32 for char in transaction_type
                ):
                    raise CSVValidationError(
                        "transaction type must be at most 80 characters without control characters"
                    )
                if has_amount:
                    amount = parse_money(values["amount"])
                else:
                    debit_text, credit_text = values["debit"], values["credit"]
                    if not debit_text and not credit_text:
                        raise CSVValidationError(
                            "include a debit or credit amount, even for zero"
                        )
                    debit = parse_money(debit_text) if debit_text else Decimal(0)
                    credit = parse_money(credit_text) if credit_text else Decimal(0)
                    if debit < 0 or credit < 0:
                        raise CSVValidationError("Debit and Credit must be nonnegative")
                    if debit > 0 and credit > 0:
                        raise CSVValidationError(
                            "Debit and Credit cannot both be positive"
                        )
                    amount = credit - debit
                transactions.append(
                    ParsedTransaction(
                        row_number, date, description, amount, transaction_type
                    )
                )
            except CSVValidationError as error:
                error_count += 1
                if len(errors) < 20:
                    errors.append(f"Row {row_number}: {error}.")
        if errors:
            remainder = (
                f" Plus {error_count - 20} more invalid rows."
                if error_count > 20
                else ""
            )
            raise CSVValidationError(
                " ".join(errors) + remainder + " Nothing was imported."
            )
    except csv.Error:
        raise CSVValidationError(
            f"Malformed CSV near line {reader.line_num}. Check quoting and commas."
        ) from None

    if not transactions:
        raise CSVValidationError("Include at least one transaction after the header.")
    counts = Counter(
        (row.date, row.description.casefold(), row.amount) for row in transactions
    )
    for row in transactions:
        row.possible_duplicate = (
            counts[(row.date, row.description.casefold(), row.amount)] > 1
        )
    return transactions
