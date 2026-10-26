"""Bounded CSV parsing with explicit interpretation and atomic validation."""

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .domain import MAX_AMOUNT_MINOR, MAX_FILE_BYTES, MAX_ROWS, ImportOptions


class ImportFailure(ValueError):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__("Statement validation failed. Nothing was imported.")


def fail(message: str, row: int | None = None, field: str | None = None):
    return {"row": row, "field": field, "message": message}


@dataclass(frozen=True)
class ParsedRow:
    source_row: int
    date: str
    description: str
    amount_minor: int


def read_csv(content: bytes):
    if len(content) > MAX_FILE_BYTES:
        raise ImportFailure([fail("File exceeds the 2 MiB limit.")])
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportFailure([fail("Use a UTF-8 encoded CSV file.")]) from exc
    if "\x00" in text:
        raise ImportFailure([fail("NUL characters are not supported.")])
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    records = []
    blanks = 0
    try:
        while True:
            start = reader.line_num + 1
            try:
                cells = next(reader)
            except StopIteration:
                break
            if not cells or all(not cell.strip() for cell in cells):
                blanks += 1
                continue
            records.append((start, cells))
            if len(records) > MAX_ROWS + 1:
                raise ImportFailure([fail(f"Maximum {MAX_ROWS:,} transaction rows.", start)])
    except csv.Error as exc:
        raise ImportFailure([fail(f"Malformed CSV: {exc}", reader.line_num)]) from exc
    if not records:
        raise ImportFailure([fail("The file is empty. Include headers and transaction rows.")])
    headers = [s.strip() for s in records[0][1]]
    if any(not h for h in headers) or len(headers) != len(set(headers)):
        raise ImportFailure([fail("Column headers must be nonempty and unique.", records[0][0])])
    if len(headers) > 50 or any(len(h) > 100 for h in headers):
        raise ImportFailure([fail("Use at most 50 columns and headers of at most 100 characters.")])
    if len(records) == 1:
        raise ImportFailure([fail("The file has headers but no transactions.")])
    errors = [
        fail(f"Expected {len(headers)} fields; found {len(cells)}.", line)
        for line, cells in records[1:]
        if len(cells) != len(headers)
    ]
    if errors:
        raise ImportFailure(errors)
    return headers, records[1:], blanks


def parse_amount(raw: str) -> int:
    value = raw.strip()
    if not value:
        raise ValueError("Amount is required.")
    if len(value) > 40:
        raise ValueError("Amount is too long; maximum 40 characters.")
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    # Commas must be correctly grouped; disallow symbols, exponents and decimal commas.
    if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?", value):
        raise ValueError("Use a decimal amount with at most 2 decimal places (e.g. -1,250.00).")
    try:
        amount = Decimal(value.replace(",", "")) * 100
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal amount.") from exc
    if not amount.is_finite() or abs(amount) > MAX_AMOUNT_MINOR:
        raise ValueError("Amount is outside the supported range (±10 billion).")
    return int(amount)


def preview(content: bytes):
    headers, records, blanks = read_csv(content)
    aliases = {
        "date_column": ("date", "transaction date", "posted date"),
        "description_column": ("description", "merchant", "details", "narration"),
        "amount_column": ("amount", "transaction amount"),
        "debit_column": ("debit", "withdrawal", "money out"),
        "credit_column": ("credit", "deposit", "money in"),
    }
    suggestions = {
        field: next((h for h in headers if h.casefold() in names), "")
        for field, names in aliases.items()
    }
    return {
        "headers": headers,
        "rows": [{"source_row": n, "cells": c} for n, c in records[:5]],
        "row_count": len(records),
        "blank_rows": blanks,
        "suggestions": suggestions,
    }


def parse_statement(content: bytes, options: ImportOptions):
    headers, records, blanks = read_csv(content)
    mapped = [options.date_column, options.description_column]
    mapped += (
        [options.amount_column]
        if options.mode == "signed"
        else [options.debit_column, options.credit_column]
    )
    missing = [name for name in mapped if name not in headers]
    if missing:
        raise ImportFailure([fail(f"Mapped column not found: {name}") for name in missing])
    formats = {"iso": "%Y-%m-%d", "dmy": "%d/%m/%Y", "mdy": "%m/%d/%Y"}
    patterns = {
        "iso": r"\d{4}-\d{2}-\d{2}",
        "dmy": r"\d{2}/\d{2}/\d{4}",
        "mdy": r"\d{2}/\d{2}/\d{4}",
    }
    results, errors = [], []
    for line, cells in records:
        row = dict(zip(headers, cells, strict=True))
        currency_columns = [h for h in headers if h.casefold() == "currency"]
        if any(
            row[h].strip() and row[h].strip().upper() != options.currency for h in currency_columns
        ):
            errors.append(
                fail("Row currency differs from the selected statement currency.", line, "currency")
            )
            continue
        try:
            raw_date = row[options.date_column].strip()
            if not re.fullmatch(patterns[options.date_format], raw_date):
                raise ValueError("Date does not match the selected format.")
            date = datetime.strptime(raw_date, formats[options.date_format]).date().isoformat()
        except ValueError:
            errors.append(fail("Invalid date for the selected format.", line, "date"))
            continue
        description = row[options.description_column]
        if not description.strip() or len(description) > 1000:
            errors.append(fail("Description must contain 1–1,000 characters.", line, "description"))
            continue
        try:
            if options.mode == "signed":
                amount = parse_amount(row[options.amount_column])
                if options.sign_convention == "positive_outgoing":
                    amount = -amount
            else:
                debit_raw, credit_raw = row[options.debit_column], row[options.credit_column]
                if not debit_raw.strip() and not credit_raw.strip():
                    raise ValueError("Enter a debit or credit amount; both are blank.")
                debit = parse_amount(debit_raw) if debit_raw.strip() else 0
                credit = parse_amount(credit_raw) if credit_raw.strip() else 0
                if debit < 0 or credit < 0 or (debit and credit):
                    raise ValueError("Debit/credit must be nonnegative; only one may be nonzero.")
                amount = credit - debit
        except ValueError as exc:
            errors.append(fail(str(exc), line, "amount"))
            continue
        results.append(ParsedRow(line, date, description, amount))
    if errors:
        raise ImportFailure(errors)
    return results, blanks
