"""SQLite persistence, atomic imports, optimistic edits, and append-only review history."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .domain import ENGINE_VERSION, ImportOptions, ParsedTransaction
from .engine import categorize, normalize


class ConflictError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def transaction_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["review_flags"] = json.loads(result["review_flags"])
    result["original_decision"] = json.loads(result["original_decision"])
    result["excluded"] = bool(result["excluded"])
    return result


class Store:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        # A fresh connection per operation keeps worker threads from sharing cursors.
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise RuntimeError("Unsupported database schema. Use a compatible application version.")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS statements (
                    id TEXT PRIMARY KEY, filename TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
                    currency TEXT NOT NULL, amount_mode TEXT NOT NULL, date_format TEXT NOT NULL,
                    engine_version TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY, statement_id TEXT NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
                    source_row INTEGER NOT NULL, date TEXT NOT NULL, description TEXT NOT NULL,
                    normalized_description TEXT NOT NULL, amount_minor INTEGER NOT NULL,
                    currency TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    category TEXT NOT NULL, kind TEXT NOT NULL, confidence REAL NOT NULL,
                    rule_id TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL,
                    review_flags TEXT NOT NULL, duplicate_of TEXT, original_decision TEXT NOT NULL,
                    excluded INTEGER NOT NULL DEFAULT 0 CHECK (excluded IN (0, 1)),
                    version INTEGER NOT NULL DEFAULT 1, note TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_transactions_statement ON transactions(statement_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_fingerprint ON transactions(fingerprint);
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY, transaction_id TEXT NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL, previous_value TEXT NOT NULL, new_value TEXT NOT NULL,
                    note TEXT NOT NULL
                );
                PRAGMA user_version = 1;
            """)

    def import_statement(
        self, filename: str, content: bytes, options: ImportOptions, parsed: list[ParsedTransaction]
    ) -> tuple[str, bool]:
        digest = hashlib.sha256(content).hexdigest()
        with self.connect() as conn:
            # Lock before checking hashes: simultaneous uploads cannot both insert duplicates.
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT * FROM statements WHERE sha256 = ?", (digest,)).fetchone()
            if existing:
                if (existing["currency"], existing["amount_mode"], existing["date_format"]) != (
                    options.currency,
                    options.amount_mode,
                    options.date_format,
                ):
                    raise ConflictError(
                        "This file was imported with different settings. Delete that import before correcting its settings."
                    )
                return existing["id"], True
            statement_id = str(uuid4())
            conn.execute(
                "INSERT INTO statements VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    statement_id,
                    filename,
                    digest,
                    options.currency,
                    options.amount_mode,
                    options.date_format,
                    ENGINE_VERSION,
                    utc_now(),
                ),
            )
            for tx in parsed:
                decision = categorize(tx)
                normalized = normalize(tx.description)
                fingerprint = hashlib.sha256(
                    json.dumps([tx.date, normalized, tx.amount_minor, tx.currency]).encode()
                ).hexdigest()
                duplicate = conn.execute(
                    "SELECT id FROM transactions WHERE fingerprint = ? AND excluded = 0 ORDER BY rowid LIMIT 1",
                    (fingerprint,),
                ).fetchone()
                flags = (["possible_duplicate"] if duplicate else []) + (["pending"] if tx.pending else [])
                reason = decision.reason
                if duplicate:
                    reason += (
                        " Same date, description, amount and currency as another row; confirm whether both are real."
                    )
                if tx.pending:
                    reason += (
                        " Pending rows are withheld; exclude this row and import the posted transaction when available."
                    )
                original = {
                    "category": decision.category,
                    "kind": decision.kind,
                    "confidence": decision.confidence,
                    "rule_id": decision.rule_id,
                    "reason": reason,
                    "engine_version": ENGINE_VERSION,
                }
                conn.execute(
                    """INSERT INTO transactions (
                    id, statement_id, source_row, date, description, normalized_description,
                    amount_minor, currency, fingerprint, category, kind, confidence, rule_id, reason,
                    status, review_flags, duplicate_of, original_decision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid4()),
                        statement_id,
                        tx.source_row,
                        tx.date,
                        tx.description,
                        normalized,
                        tx.amount_minor,
                        tx.currency,
                        fingerprint,
                        decision.category,
                        decision.kind,
                        decision.confidence,
                        decision.rule_id,
                        reason,
                        "needs_review" if flags or decision.needs_review else "auto",
                        json.dumps(flags),
                        duplicate["id"] if duplicate else None,
                        json.dumps(original),
                    ),
                )
        return statement_id, False

    def list_statements(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("""SELECT s.*, COUNT(t.id) AS transaction_count,
                COALESCE(SUM(t.status = 'needs_review'), 0) AS review_count
                FROM statements s LEFT JOIN transactions t ON s.id = t.statement_id
                GROUP BY s.id ORDER BY s.created_at DESC""").fetchall()
            return [dict(row) for row in rows]

    def get_statement(self, statement_id: str) -> dict | None:
        with self.connect() as conn:
            statement = conn.execute("SELECT * FROM statements WHERE id = ?", (statement_id,)).fetchone()
            if not statement:
                return None
            rows = conn.execute(
                "SELECT * FROM transactions WHERE statement_id = ? ORDER BY source_row", (statement_id,)
            ).fetchall()
            return {**dict(statement), "transactions": [transaction_dict(row) for row in rows]}

    def review(self, transaction_id: str, changes: dict) -> dict | None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
            if not row:
                return None
            previous = transaction_dict(row)
            if previous["version"] != changes["expected_version"]:
                raise ConflictError("This transaction changed in another tab. Refresh and review the latest version.")
            validate_review(previous, changes)
            conn.execute(
                """UPDATE transactions SET category = ?, kind = ?, excluded = ?, note = ?,
                status = 'reviewed', version = version + 1 WHERE id = ?""",
                (changes["category"], changes["kind"], int(changes["excluded"]), changes["note"], transaction_id),
            )
            updated = transaction_dict(
                conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
            )
            # Machine evidence remains immutable; overrides are separate, auditable events.
            conn.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid4()), transaction_id, utc_now(), json.dumps(previous), json.dumps(updated), changes["note"]),
            )
            return updated

    def audit(self, statement_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT a.* FROM audit_events a JOIN transactions t ON t.id = a.transaction_id
                WHERE t.statement_id = ? ORDER BY a.created_at, a.rowid""",
                (statement_id,),
            ).fetchall()
            return [
                {
                    **dict(row),
                    "previous_value": json.loads(row["previous_value"]),
                    "new_value": json.loads(row["new_value"]),
                }
                for row in rows
            ]

    def delete_statement(self, statement_id: str) -> bool:
        with self.connect() as conn:
            return conn.execute("DELETE FROM statements WHERE id = ?", (statement_id,)).rowcount == 1


def validate_review(row: dict, changes: dict):
    """The server, never the UI alone, enforces accounting direction and category pairing."""
    from .domain import EXPENSE_CATEGORIES, Category, Kind

    if changes["excluded"]:
        if len(changes["note"].strip()) < 3:
            raise ValueError("Add a reason when excluding a row.")
        return
    if "pending" in row["review_flags"]:
        raise ValueError(
            "Pending transactions cannot count toward totals. Exclude this row and import its posted version."
        )
    kind, category, amount = changes["kind"], changes["category"], row["amount_minor"]
    if amount == 0:
        raise ValueError("Zero-value transactions must be excluded with a note.")
    if kind == Kind.UNKNOWN or category == Category.REVIEW:
        raise ValueError("Choose a category and money movement before confirming.")
    if kind == Kind.EXPENSE and amount >= 0:
        raise ValueError("An expense must be money out (negative normalized amount).")
    if kind in (Kind.REFUND, Kind.INCOME) and amount <= 0:
        raise ValueError("Refunds and income must be money in (positive normalized amount).")
    expected = {Kind.INCOME: Category.INCOME, Kind.TRANSFER: Category.TRANSFERS, Kind.PERSONAL: Category.PERSONAL}
    if kind in expected and category != expected[kind]:
        raise ValueError(f"{kind.title()} must use the {expected[kind]} category.")
    if kind in (Kind.EXPENSE, Kind.REFUND) and category not in EXPENSE_CATEGORIES:
        raise ValueError("Expenses and refunds must use an expense category.")
