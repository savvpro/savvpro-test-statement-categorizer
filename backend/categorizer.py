import csv
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation


MERCHANT_RULES = {
    "Software": ["ADOBE", "FIGMA", "CANVA", "GITHUB"],
    "Travel": ["UBER", "CAREEM"],
    "Internet": ["PTCL", "NAYATEL"],
}

TRANSFER_PHRASES = [
    "TRANSFER TO SAVINGS",
    "TRANSFER FROM SAVINGS",
    "INTERNAL TRANSFER",
    "CREDIT CARD PAYMENT",
]


def contains_phrase(text, phrase):
    return re.search(r"\b" + re.escape(phrase) + r"\b", text) is not None


def classify(description, amount):
    text = " ".join(
        re.sub(r"[^A-Z0-9]+", " ", description.upper()).split()
    )

    def result(kind, category, reason, review=False):
        return {
            "type": kind,
            "category": category,
            "reason": reason,
            "needs_review": review,
        }

    def uncertain(reason):
        return result("unknown", "Needs Review", reason, True)

    if amount == 0:
        return uncertain("Zero amount requires review.")

    is_transfer = any(
        contains_phrase(text, phrase)
        for phrase in TRANSFER_PHRASES
    )
    is_refund = contains_phrase(text, "REFUND")
    is_income = contains_phrase(text, "CLIENT PAYMENT")

    if sum([is_transfer, is_refund, is_income]) > 1:
        return uncertain("Conflicting transaction indicators.")

    if is_transfer:
        return result(
            "transfer",
            "Transfer",
            "Explicit transfer or credit-card payment; excluded from spending.",
        )

    matches = {
        category
        for category, merchants in MERCHANT_RULES.items()
        if any(contains_phrase(text, merchant) for merchant in merchants)
    }

    if len(matches) > 1:
        return uncertain("Description matches multiple categories.")

    category = next(iter(matches), None)

    if is_refund:
        if amount < 0:
            return uncertain("Refund description has an outgoing amount.")

        if category:
            return result(
                "refund",
                category,
                "Refund reduces spending in the matched category.",
            )

        return result(
            "refund",
            "Needs Review",
            "Refund identified, but its expense category is unknown.",
            True,
        )

    if is_income:
        if amount < 0 or category:
            return uncertain("Client payment has conflicting details.")

        return result(
            "income",
            "Client Income",
            "Incoming amount with explicit client-payment description.",
        )

    if amount > 0:
        return uncertain("Incoming money is not automatically income.")

    if category:
        return result(
            "expense",
            category,
            f"Merchant rule matched {category}; verify business purpose.",
        )

    return uncertain("No reliable categorization rule matched.")


def parse_statement(content):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Please upload a UTF-8 CSV file.")

    reader = csv.DictReader(io.StringIO(text), strict=True)
    required = {"date", "description", "amount", "currency"}

    if not reader.fieldnames:
        raise ValueError("The CSV file is empty.")

    headers = [header.strip().lower() for header in reader.fieldnames]

    if len(headers) != len(set(headers)):
        raise ValueError("Duplicate column names are not allowed.")

    if not required.issubset(headers):
        raise ValueError(
            "Required columns: date, description, amount, currency."
        )

    reader.fieldnames = headers
    transactions = []
    currencies = set()

    try:
        for row_number, row in enumerate(reader, start=2):
            if len(transactions) >= 5000:
                raise ValueError("Maximum 5,000 transactions per upload.")

            if None in row or any(row.get(key) is None for key in required):
                raise ValueError(
                    f"Row {row_number}: incorrect number of columns."
                )

            raw_date = row["date"].strip()
            description = row["description"].strip()
            raw_amount = row["amount"].strip()
            currency = row["currency"].strip().upper()

            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
                    raise ValueError()
                date.fromisoformat(raw_date)
            except ValueError:
                raise ValueError(
                    f"Row {row_number}: use a valid YYYY-MM-DD date."
                )

            if not description:
                raise ValueError(
                    f"Row {row_number}: description cannot be empty."
                )

            if len(description) > 500:
                raise ValueError(
                    f"Row {row_number}: description exceeds 500 characters."
                )

            if not re.fullmatch(r"[+-]?\d+(?:\.\d{1,2})?", raw_amount):
                raise ValueError(
                    f"Row {row_number}: amount must be a number "
                    "with at most two decimal places, without commas."
                )

            try:
                amount = Decimal(raw_amount)
            except InvalidOperation:
                raise ValueError(f"Row {row_number}: invalid amount.")

            if abs(amount) > Decimal("999999999999.99"):
                raise ValueError(f"Row {row_number}: amount is too large.")

            if currency not in {"PKR", "USD", "GBP", "EUR", "SAR", "AED"}:
                raise ValueError(
                    f"Row {row_number}: supported currencies are "
                    "PKR, USD, GBP, EUR, SAR and AED."
                )

            currencies.add(currency)
            if len(currencies) > 1:
                raise ValueError("Use only one currency per statement.")

            transactions.append({
                "id": len(transactions) + 1,
                "date": raw_date,
                "description": description,
                "amount": format(amount, ".2f"),
                "currency": currency,
                **classify(description, amount),
            })

    except csv.Error:
        raise ValueError("Malformed CSV. Check quotation marks and columns.")

    if not transactions:
        raise ValueError("The CSV contains no transactions.")

    return transactions