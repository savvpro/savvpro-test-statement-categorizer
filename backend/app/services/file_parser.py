from pathlib import Path
import re

import pandas as pd


COLUMN_ALIASES = {
    "date": {
        "date", "transaction date", "posting date", "trans date",
    },
    "description": {
        "description", "transaction description", "transaction details",
        "details", "narration", "merchant", "payee", "memo",
    },
    "amount": {
        "amount", "transaction amount", "value",
    },
    "debit": {
        "debit", "withdrawal", "withdrawals", "money out",
        "debit amount",
    },
    "credit": {
        "credit", "deposit", "deposits", "money in",
        "credit amount",
    },
    "currency": {"currency", "ccy"},
    "balance": {"balance", "running balance", "available balance"},
}


def normalize_column_name(name: object) -> str:
    text = str(name).strip().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def identify_columns(columns) -> dict[str, str]:
    """Map recognized logical fields to their original column names."""
    aliases = {
        field: {normalize_column_name(alias) for alias in names}
        for field, names in COLUMN_ALIASES.items()
    }

    identified = {}
    for column in columns:
        normalized = normalize_column_name(column)
        for field, names in aliases.items():
            if field not in identified and normalized in names:
                identified[field] = column

    return identified


def parse_statement(file_path: str | Path) -> dict:
    """Parse a statement and validate its required transaction columns."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Statement file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        dataframe = pd.read_csv(path)
    elif suffix in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(path)
    else:
        raise ValueError("Unsupported file type. Upload CSV, XLSX, or XLS.")

    if dataframe.empty and len(dataframe.columns) == 0:
        raise ValueError("The uploaded statement has no columns.")

    columns = identify_columns(dataframe.columns)

    missing = []
    if "date" not in columns:
        missing.append("date")
    if "description" not in columns:
        missing.append("description")
    if "amount" not in columns and not (
        "debit" in columns and "credit" in columns
    ):
        missing.append("amount or both debit and credit")

    if missing:
        return {
            "valid": False,
            "missing_columns": missing,
            "identified_columns": columns,
            "transactions": [],
            "errors": [
                "Missing required columns: " + ", ".join(missing)
            ],
        }

    transactions = []

    for index, row in dataframe.iterrows():
        date_value = row[columns["date"]]
        description_value = row[columns["description"]]

        if pd.isna(date_value) or pd.isna(description_value):
            continue

        description = str(description_value).strip()
        if not description:
            continue

        if "amount" in columns:
            amount = pd.to_numeric(row[columns["amount"]], errors="coerce")
        else:
            debit = pd.to_numeric(row[columns["debit"]], errors="coerce")
            credit = pd.to_numeric(row[columns["credit"]], errors="coerce")

            debit = 0.0 if pd.isna(debit) else float(debit)
            credit = 0.0 if pd.isna(credit) else float(credit)

            if debit and credit:
                continue

            amount = credit - debit

        if pd.isna(amount):
            continue

        transaction = {
            "date": pd.Timestamp(date_value).date().isoformat(),
            "description": description,
            "amount": round(float(amount), 2),
            "currency": (
                str(row[columns["currency"]]).strip()
                if "currency" in columns
                and pd.notna(row[columns["currency"]])
                else None
            ),
            "balance": None,
            "source_row": int(index) + 2,
        }

        if "balance" in columns and pd.notna(row[columns["balance"]]):
            balance = pd.to_numeric(row[columns["balance"]], errors="coerce")
            if pd.notna(balance):
                transaction["balance"] = round(float(balance), 2)

        transactions.append(transaction)

    return {
        "valid": True,
        "missing_columns": [],
        "identified_columns": columns,
        "transactions": transactions,
        "errors": [],
    }