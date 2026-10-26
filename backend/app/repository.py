"""SQLite persistence. Each import or correction is a single transaction."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from backend.app.engine import classify
from backend.app.parser import ParsedStatement
from backend.app.service import validate_review


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Repository:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS statements (
                    id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL, currency TEXT NOT NULL,
                    created_at TEXT NOT NULL, options TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY, statement_id TEXT NOT NULL
                        REFERENCES statements(id) ON DELETE CASCADE,
                    date TEXT NOT NULL, description TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL, source_id TEXT NOT NULL,
                    row_number INTEGER NOT NULL, duplicate_of INTEGER,
                    category TEXT, kind TEXT NOT NULL, status TEXT NOT NULL,
                    reason TEXT NOT NULL, rule_id TEXT NOT NULL,
                    original_category TEXT, original_kind TEXT NOT NULL,
                    original_reason TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_transaction_statement
                    ON transactions(statement_id, row_number);
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT NOT NULL REFERENCES transactions(id),
                    previous_category TEXT, previous_kind TEXT NOT NULL,
                    category TEXT NOT NULL, kind TEXT NOT NULL,
                    note TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def import_statement(
        self, parsed: ParsedStatement, filename: str, fingerprint: str, options: dict
    ) -> tuple[str, bool]:
        with self.connect() as db:
            # Serialize check + insert; the unique fingerprint is a second safeguard.
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT id FROM statements WHERE fingerprint=?", (fingerprint,)
            ).fetchone()
            if existing:
                return existing["id"], False
            statement_id = str(uuid4())
            db.execute(
                "INSERT INTO statements VALUES (?, ?, ?, ?, ?, ?)",
                (
                    statement_id,
                    fingerprint,
                    filename,
                    parsed.currency,
                    utc_now(),
                    json.dumps(options),
                ),
            )
            for raw in parsed.transactions:
                decision = classify(raw.description, raw.amount_cents)
                values = {
                    **asdict(raw),
                    **asdict(decision),
                    "id": str(uuid4()),
                    "statement_id": statement_id,
                    "original_category": decision.category,
                    "original_kind": decision.kind,
                    "original_reason": decision.reason,
                }
                if raw.duplicate_of:
                    values.update(
                        category=None,
                        status="needs_review",
                        reason=f"Possible duplicate of row {raw.duplicate_of}. "
                        "Exclude it or confirm this is a separate transaction.",
                        rule_id="possible_duplicate",
                    )
                columns = ", ".join(values)
                placeholders = ", ".join("?" for _ in values)
                db.execute(
                    f"INSERT INTO transactions ({columns}) VALUES ({placeholders})",
                    tuple(values.values()),
                )
            return statement_id, True

    def list_statements(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("""
                SELECT s.id, s.filename, s.currency, s.created_at,
                       COUNT(t.id) AS transaction_count,
                       SUM(CASE WHEN t.status='needs_review' THEN 1 ELSE 0 END) AS needs_review
                FROM statements s LEFT JOIN transactions t ON t.statement_id=s.id
                GROUP BY s.id ORDER BY s.created_at DESC
            """).fetchall()
            return [dict(row) for row in rows]

    def get_statement(self, statement_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM statements WHERE id=?", (statement_id,)).fetchone()
            if not row:
                raise NotFoundError("Statement not found.")
            statement = dict(row)
            statement.pop("fingerprint")
            statement["options"] = json.loads(statement["options"])
            transactions = [
                dict(t)
                for t in db.execute(
                    "SELECT * FROM transactions WHERE statement_id=? ORDER BY row_number",
                    (statement_id,),
                )
            ]
            history: dict[str, list] = {}
            for review in db.execute(
                """
                SELECT r.* FROM reviews r JOIN transactions t ON t.id=r.transaction_id
                WHERE t.statement_id=? ORDER BY r.id DESC
            """,
                (statement_id,),
            ):
                history.setdefault(review["transaction_id"], []).append(dict(review))
            for transaction in transactions:
                transaction["history"] = history.get(transaction["id"], [])
            statement["transactions"] = transactions
            return statement

    def review(
        self,
        statement_id: str,
        transaction_id: str,
        *,
        category: str,
        kind: str,
        note: str,
        revision: int,
    ) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM transactions WHERE id=? AND statement_id=?",
                (transaction_id, statement_id),
            ).fetchone()
            if not row:
                raise NotFoundError("Transaction not found.")
            if row["revision"] != revision:
                raise ConflictError("This row changed in another session. Refresh and try again.")
            validate_review(row["amount_cents"], category, kind)
            db.execute(
                """
                INSERT INTO reviews (transaction_id, previous_category, previous_kind,
                    category, kind, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (transaction_id, row["category"], row["kind"], category, kind, note, utc_now()),
            )
            db.execute(
                """
                UPDATE transactions SET category=?, kind=?, status='reviewed',
                reason='Confirmed by you.', note=?, revision=revision+1 WHERE id=?
            """,
                (category, kind, note, transaction_id),
            )
