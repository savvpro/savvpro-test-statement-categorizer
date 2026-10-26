"""Header synonym map for flexible CSV column detection."""
from __future__ import annotations

# Maps canonical role → list of recognized header names (case-insensitive)
HEADER_SYNONYMS: dict[str, list[str]] = {
    "date": [
        "date", "posting date", "post date", "posted date",
        "trans date", "transaction date", "value date",
        "settlement date", "cleared date",
    ],
    "description": [
        "description", "payee", "name", "details", "memo",
        "transaction description", "transaction detail",
        "narrative", "reference", "particulars",
    ],
    "amount": [
        "amount", "transaction amount", "net amount",
        "total", "total amount",
    ],
    "debit": [
        "debit", "debit amount", "withdrawal", "withdrawals",
        "out", "charge", "charges",
    ],
    "credit": [
        "credit", "credit amount", "deposit", "deposits",
        "in", "payment", "payments",
    ],
    "balance": [
        "balance", "running balance", "available balance",
        "account balance", "closing balance",
    ],
}

# These column names strongly suggest this is a summary/total/balance row
FOOTER_COLUMN_HINTS = {"balance", "running balance"}


def detect_column(header: str) -> str | None:
    """Return canonical role for a header name, or None if unrecognized."""
    normalized = header.strip().lower()
    for role, synonyms in HEADER_SYNONYMS.items():
        if normalized in synonyms:
            return role
    # Combined headers such as "Payee / Description": match on any one part
    parts = [p.strip() for p in normalized.split("/")]
    if len(parts) > 1:
        for part in parts:
            for role, synonyms in HEADER_SYNONYMS.items():
                if part in synonyms:
                    return role
    return None


def map_headers(headers: list[str]) -> dict[str, int]:
    """Return {role: column_index} for all recognized headers.

    Handles both Amount-only and Debit/Credit split layouts.
    """
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        role = detect_column(h)
        if role and role not in mapping:
            mapping[role] = i
    return mapping
