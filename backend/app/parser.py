import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation


REQUIRED_COLUMNS = {"date", "description", "amount"}


class StatementParseError(ValueError):
    pass


def parse_statement(content: bytes) -> list[dict[str, str | int]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise StatementParseError("The statement must be a UTF-8 CSV file.") from error

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise StatementParseError("The CSV must include date, description, and amount columns.")

    columns = {column.strip().lower() for column in reader.fieldnames if column}
    missing_columns = REQUIRED_COLUMNS - columns
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise StatementParseError(f"Missing required column(s): {missing}.")

    transactions: list[dict[str, str | int]] = []
    for row_number, row in enumerate(reader, start=2):
        normalized = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
        }
        description = normalized.get("description", "")
        amount = normalized.get("amount", "")
        transaction_date = normalized.get("date", "")

        if not description:
            raise StatementParseError(f"Row {row_number}: description is required.")
        try:
            parsed_date = date.fromisoformat(transaction_date)
        except ValueError as error:
            raise StatementParseError(
                f"Row {row_number}: date must use YYYY-MM-DD format."
            ) from error
        try:
            parsed_amount = Decimal(amount.replace(",", "").replace("$", ""))
        except InvalidOperation as error:
            raise StatementParseError(f"Row {row_number}: amount must be a number.") from error

        transactions.append(
            {
                "source_row": row_number,
                "date": parsed_date.isoformat(),
                "description": description,
                "amount": str(parsed_amount),
            }
        )

    if not transactions:
        raise StatementParseError("The CSV does not contain any transactions.")
    return transactions