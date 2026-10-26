"""Column names the app understands, shared by the CSV and PDF parsers.

If a bank uses a header that isn't listed here, the upload fails with a
message naming the missing column. Adding a name here is the fix.
"""

import re

COLUMN_ALIASES: dict[str, set[str]] = {
    "date": {"date", "transaction date", "txn date", "trans date", "value date", "posting date", "booking date"},
    "description": {
        "description", "details", "transaction details", "narration", "particulars",
        "remarks", "transaction description", "memo",
    },
    "amount": {"amount", "transaction amount", "amt"},
    "debit": {"debit", "debits", "withdrawal", "withdrawals", "dr", "money out", "paid out", "debit amount"},
    "credit": {"credit", "credits", "deposit", "deposits", "cr", "money in", "paid in", "credit amount"},
    "balance": {"balance", "running balance", "available balance", "closing balance"},
    "type": {"type", "dr/cr", "cr/dr", "debit/credit", "transaction type"},
    "currency": {"currency", "ccy", "cur"},
}


def canonical_column(header: str) -> tuple[str | None, str | None]:
    """'Debit (PKR)' -> ('debit', 'PKR'). Returns the column role and any currency in brackets."""
    text = (header or "").strip().lower()
    currency = None
    bracket = re.search(r"[\(\[]\s*(pkr|usd|rs\.?|\$)\s*[\)\]]", text)
    if bracket:
        token = bracket.group(1)
        currency = "USD" if token in {"usd", "$"} else "PKR"
        text = (text[: bracket.start()] + text[bracket.end():]).strip()
    text = re.sub(r"\s+", " ", text.replace("_", " ")).strip(" .:")
    for role, names in COLUMN_ALIASES.items():
        if text in names:
            return role, currency
    return None, currency


def describe_supported() -> str:
    return "; ".join(f"{role}: {', '.join(sorted(names))}" for role, names in COLUMN_ALIASES.items())
