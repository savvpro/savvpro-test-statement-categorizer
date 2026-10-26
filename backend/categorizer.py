"""Deterministic statement categorizer for simplke.

This module intentionally uses no machine learning or large language model. It parses a
freelance designer's synthetic statement CSV, normalizes rows, and applies ordered rules.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterable, Mapping

CATEGORIES = [
    "Software",
    "Travel",
    "Meals",
    "Office supplies",
    "Equipment",
    "Advertising",
    "Bank fees",
    "Refund",
    "Income",
    "Transfer / non-spend",
    "Needs review",
]

HEADER_ALIASES = {
    "date": {"date", "transactiondate", "posteddate", "postingdate"},
    "description": {"description", "merchant", "details", "memo", "payee", "transaction"},
    "amount": {"amount", "transactionamount", "value"},
    "type": {"type", "transactiontype", "debitcredit", "direction"},
}

@dataclass(frozen=True)
class Decision:
    category: str
    status: str
    confidence: str
    rule_id: str
    rule_label: str
    review_reason: str | None = None

@dataclass
class Transaction:
    id: str
    date: str
    description: str
    amount: float | None
    direction: str
    category: str
    status: str
    confidence: str
    rule_id: str
    rule_label: str
    review_reason: str | None
    raw: dict[str, str]


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def map_headers(headers: Iterable[str]) -> dict[str, str]:
    """Map flexible statement headers to canonical field names."""
    mapping: dict[str, str] = {}
    normalized = {_header_key(header): header for header in headers}
    for canonical, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[canonical] = normalized[alias]
                break
    return mapping


def parse_amount(value: str | None, direction: str = "") -> float | None:
    if value is None or not value.strip():
        return None
    cleaned = value.strip().upper().replace("$", "").replace(",", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    direction = direction.strip().lower()
    if direction in {"debit", "expense", "withdrawal", "outflow"}:
        amount = -abs(amount)
    elif direction in {"credit", "income", "deposit", "inflow"}:
        amount = abs(amount)
    if negative:
        amount = -abs(amount)
    return round(amount, 2)


def normalize_description(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().upper())


def _contains(text: str, terms: tuple[str, ...]) -> str | None:
    for term in terms:
        if term in text:
            return term
    return None


def classify(description: str, amount: float | None, direction: str, data_issue: str | None = None) -> Decision:
    """Return one explainable decision. Rules are ordered from safest to broadest."""
    text = normalize_description(description)
    if data_issue or amount is None or not text:
        return Decision("Needs review", "needs_review", "review", "data-quality", data_issue or "Missing description or amount.", data_issue or "Missing description or amount.")

    matched = _contains(text, ("TRANSFER", "AUTOPAY", "AUTO PAY", "CARD PAYMENT", "PAYMENT TO", "CASH ADVANCE", "SAVINGS"))
    if matched:
        return Decision("Transfer / non-spend", "categorized", "high", "transfer", f"Merchant text contains “{matched}”")

    matched = _contains(text, ("REFUND", "RETURN", "REVERSAL", "CREDIT MEMO", "CHARGEBACK"))
    if matched:
        return Decision("Refund", "categorized", "high", "refund", f"Merchant text contains “{matched}”")

    matched = _contains(text, ("CLIENT PAYMENT", "INVOICE", "PAYOUT", "PROJECT DEPOSIT", "CONTRACTOR PAYMENT"))
    if matched and amount > 0:
        return Decision("Income", "categorized", "high", "income", f"Direction is credit and description contains “{matched}”")

    matched = _contains(text, ("BANK FEE", "SERVICE FEE", "OVERDRAFT", "FOREIGN TRANSACTION FEE", "MONTHLY FEE"))
    if matched:
        return Decision("Bank fees", "categorized", "high", "fees", f"Merchant text contains “{matched}”")

    rule_groups = (
        ("software", "Software", ("ADOBE", "FIGMA", "GITHUB", "NOTION", "DROPBOX", "GOOGLE WORKSPACE", "AIRTABLE"), "high"),
        ("travel", "Travel", ("UBER", "LYFT", "AIRBNB", "DELTA", "SOUTHWEST", "UNITED AIR", "AMTRAK", "HOTEL", "PARKING", "RIDESHARE"), "high"),
        ("meals", "Meals", ("STARBUCKS", "DOORDASH", "UBER EATS", "GRUBHUB", "COFFEE", "RESTAURANT", "CATERING"), "medium"),
        ("office-supplies", "Office supplies", ("STAPLES", "OFFICE DEPOT", "PRINTER", "PAPER", "DESK SUPPLIES"), "high"),
        ("equipment", "Equipment", ("B&H", "BEST BUY", "APPLE STORE", "DELL", "LOGITECH", "CAMERA", "MONITOR", "KEYBOARD"), "high"),
        ("advertising", "Advertising", ("META ADS", "GOOGLE ADS", "CAMPAIGN", "SPONSORED", "PROMOTED"), "high"),
    )
    for rule_id, category, terms, confidence in rule_groups:
        matched = _contains(text, terms)
        if matched:
            return Decision(category, "categorized", confidence, rule_id, f"Merchant text contains “{matched}”")

    if amount > 0:
        return Decision("Needs review", "needs_review", "review", "unmatched-credit", "Positive inflow without a recognized income or refund rule.", "Positive inflow without a recognized income or refund rule.")
    return Decision("Needs review", "needs_review", "review", "unmatched", "No specific merchant rule matched this transaction.", "No specific merchant rule matched this transaction.")


def categorize_rows(rows: Iterable[Mapping[str, str]]) -> list[Transaction]:
    rows = list(rows)
    if not rows:
        return []
    headers = list(rows[0].keys())
    mapping = map_headers(headers)
    seen: dict[tuple[str, str, float | None], int] = {}
    normalized_rows: list[tuple[str, str, float | None, str, dict[str, str], str | None]] = []
    for index, row in enumerate(rows):
        date = str(row.get(mapping.get("date", ""), "")).strip()
        description = str(row.get(mapping.get("description", ""), "")).strip()
        direction = str(row.get(mapping.get("type", ""), "")).strip()
        amount = parse_amount(str(row.get(mapping.get("amount", ""), "")), direction)
        issue = None
        if not date:
            issue = "Missing date."
        elif not description:
            issue = "Missing description."
        elif amount is None:
            issue = "Amount is missing or not numeric."
        fingerprint = (date, normalize_description(description), amount)
        if not issue and fingerprint in seen:
            issue = f"Exact duplicate of row {seen[fingerprint] + 1}."
        elif not issue:
            seen[fingerprint] = index
        normalized_rows.append((date, description, amount, direction, dict(row), issue))

    output: list[Transaction] = []
    for index, (date, description, amount, direction, raw, issue) in enumerate(normalized_rows):
        decision = classify(description, amount, direction, issue)
        output.append(Transaction(
            id=f"txn-{index + 1}",
            date=date,
            description=description,
            amount=amount,
            direction=direction or ("Credit" if (amount or 0) > 0 else "Debit"),
            category=decision.category,
            status=decision.status,
            confidence=decision.confidence,
            rule_id=decision.rule_id,
            rule_label=decision.rule_label,
            review_reason=decision.review_reason,
            raw=raw,
        ))
    return output


def categorize_csv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV needs a header row.")
    mapping = map_headers(reader.fieldnames)
    missing = [key for key in ("date", "description", "amount") if key not in mapping]
    if missing:
        raise ValueError(f"CSV is missing required column(s): {', '.join(missing)}")
    return [asdict(transaction) for transaction in categorize_rows(reader)]


def main() -> None:
    import json
    import sys

    payload = sys.stdin.read()
    print(json.dumps(categorize_csv(payload), indent=2))


if __name__ == "__main__":
    main()
