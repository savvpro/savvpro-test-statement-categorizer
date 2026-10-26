"""SQLite storage.

Money is stored as whole paisa / cents (INTEGER) so sums in SQL are exact.
The schema version lives in PRAGMA user_version; add a new step to
MIGRATIONS for each schema change instead of editing an old one.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS = [
    """
    CREATE TABLE statements (
        id            INTEGER PRIMARY KEY,
        filename      TEXT NOT NULL,
        file_hash     TEXT NOT NULL UNIQUE,
        source_kind   TEXT NOT NULL CHECK (source_kind IN ('csv', 'pdf', 'ocr')),
        account_type  TEXT NOT NULL CHECK (account_type IN ('business', 'mixed')),
        currency      TEXT NOT NULL,
        imported_at   TEXT NOT NULL,
        report_json   TEXT NOT NULL
    );

    CREATE TABLE transactions (
        id                     INTEGER PRIMARY KEY,
        statement_id           INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
        source_row             TEXT NOT NULL,
        txn_date               TEXT NOT NULL,
        description            TEXT NOT NULL,
        amount_minor           INTEGER NOT NULL,
        currency               TEXT NOT NULL CHECK (currency IN ('PKR', 'USD')),
        balance_minor          INTEGER,
        txn_type               TEXT NOT NULL,
        category               TEXT,
        suggested_category     TEXT,
        status                 TEXT NOT NULL CHECK (status IN ('auto', 'needs_review', 'user_corrected')),
        rule_id                TEXT,
        reason                 TEXT NOT NULL,
        flags_json             TEXT NOT NULL DEFAULT '[]',
        linked_txn_id          INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
        fingerprint            TEXT NOT NULL,
        app_category           TEXT,
        app_reason             TEXT,
        updated_at             TEXT NOT NULL,
        CHECK (status = 'needs_review' OR category IS NOT NULL)
    );
    CREATE INDEX ix_transactions_statement ON transactions(statement_id);
    CREATE INDEX ix_transactions_fingerprint ON transactions(fingerprint);
    CREATE INDEX ix_transactions_status ON transactions(status);

    CREATE TABLE user_rules (
        id                   INTEGER PRIMARY KEY,
        pattern              TEXT NOT NULL,
        match_type           TEXT NOT NULL CHECK (match_type IN ('exact', 'starts_with', 'contains')),
        category             TEXT NOT NULL,
        enabled              INTEGER NOT NULL DEFAULT 1,
        created_at           TEXT NOT NULL,
        created_from_txn_id  INTEGER,
        UNIQUE (pattern, match_type)
    );
    """,
]


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for step, script in enumerate(MIGRATIONS[version:], start=version + 1):
        with conn:
            conn.executescript(script)
            conn.execute(f"PRAGMA user_version = {step}")


# --- statements --------------------------------------------------------------

def find_statement_by_hash(conn, file_hash: str):
    return conn.execute("SELECT * FROM statements WHERE file_hash = ?", (file_hash,)).fetchone()


def insert_statement(conn, *, filename, file_hash, source_kind, account_type, currency, report) -> int:
    cur = conn.execute(
        """INSERT INTO statements (filename, file_hash, source_kind, account_type, currency, imported_at, report_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (filename, file_hash, source_kind, account_type, currency, now(), json.dumps(report)),
    )
    return cur.lastrowid


def update_statement_report(conn, statement_id: int, report: dict) -> None:
    conn.execute("UPDATE statements SET report_json = ? WHERE id = ?", (json.dumps(report), statement_id))


def list_statements(conn):
    return conn.execute(
        """SELECT s.*,
                  COUNT(t.id) AS row_count,
                  SUM(t.status = 'needs_review') AS review_count
           FROM statements s LEFT JOIN transactions t ON t.statement_id = s.id
           GROUP BY s.id ORDER BY s.imported_at DESC, s.id DESC"""
    ).fetchall()


def get_statement(conn, statement_id: int):
    return conn.execute("SELECT * FROM statements WHERE id = ?", (statement_id,)).fetchone()


def delete_statement(conn, statement_id: int) -> bool:
    return conn.execute("DELETE FROM statements WHERE id = ?", (statement_id,)).rowcount > 0


def delete_all(conn) -> None:
    conn.execute("DELETE FROM transactions")
    conn.execute("DELETE FROM statements")


# --- transactions ------------------------------------------------------------

TXN_COLUMNS = (
    "statement_id", "source_row", "txn_date", "description", "amount_minor", "currency", "balance_minor",
    "txn_type", "category", "suggested_category", "status", "rule_id", "reason", "flags_json",
    "linked_txn_id", "fingerprint", "app_category", "app_reason", "updated_at",
)


def insert_transaction(conn, values: dict) -> int:
    values = {**values, "updated_at": now()}
    placeholders = ", ".join("?" for _ in TXN_COLUMNS)
    cur = conn.execute(
        f"INSERT INTO transactions ({', '.join(TXN_COLUMNS)}) VALUES ({placeholders})",
        tuple(values.get(c) for c in TXN_COLUMNS),
    )
    return cur.lastrowid


def update_transaction(conn, txn_id: int, values: dict) -> None:
    allowed = {k: v for k, v in values.items() if k in TXN_COLUMNS and k != "statement_id"}
    allowed["updated_at"] = now()
    sets = ", ".join(f"{k} = ?" for k in allowed)
    conn.execute(f"UPDATE transactions SET {sets} WHERE id = ?", (*allowed.values(), txn_id))


def get_transaction(conn, txn_id: int):
    return conn.execute(
        """SELECT t.*, s.filename AS source_file, s.account_type
           FROM transactions t JOIN statements s ON s.id = t.statement_id WHERE t.id = ?""",
        (txn_id,),
    ).fetchone()


def list_transactions(conn, statement_id: int | None = None, status: str | None = None):
    sql = """SELECT t.*, s.filename AS source_file, s.account_type
             FROM transactions t JOIN statements s ON s.id = t.statement_id WHERE 1 = 1"""
    params: list = []
    if statement_id is not None:
        sql += " AND t.statement_id = ?"
        params.append(statement_id)
    if status:
        sql += " AND t.status = ?"
        params.append(status)
    sql += " ORDER BY t.txn_date, t.id"
    return conn.execute(sql, params).fetchall()


def find_by_fingerprint(conn, fingerprint: str, exclude_statement_id: int):
    return conn.execute(
        """SELECT t.id, t.source_row, s.filename FROM transactions t
           JOIN statements s ON s.id = t.statement_id
           WHERE t.fingerprint = ? AND t.statement_id <> ? LIMIT 1""",
        (fingerprint, exclude_statement_id),
    ).fetchone()


def refund_history(conn):
    """Money-out rows that a later refund could belong to."""
    return conn.execute(
        "SELECT id, txn_date, description, amount_minor, currency, rule_id, category "
        "FROM transactions WHERE amount_minor < 0"
    ).fetchall()


# --- user rules --------------------------------------------------------------

def list_user_rules(conn, enabled_only: bool = False):
    sql = "SELECT * FROM user_rules"
    if enabled_only:
        sql += " WHERE enabled = 1"
    return conn.execute(sql + " ORDER BY id").fetchall()


def insert_user_rule(conn, *, pattern, match_type, category, created_from_txn_id=None) -> int:
    cur = conn.execute(
        """INSERT INTO user_rules (pattern, match_type, category, created_at, created_from_txn_id)
           VALUES (?, ?, ?, ?, ?)""",
        (pattern, match_type, category, now(), created_from_txn_id),
    )
    return cur.lastrowid


def get_user_rule(conn, rule_id: int):
    return conn.execute("SELECT * FROM user_rules WHERE id = ?", (rule_id,)).fetchone()


def set_user_rule_enabled(conn, rule_id: int, enabled: bool) -> bool:
    return conn.execute("UPDATE user_rules SET enabled = ? WHERE id = ?", (int(enabled), rule_id)).rowcount > 0


def delete_user_rule(conn, rule_id: int) -> bool:
    return conn.execute("DELETE FROM user_rules WHERE id = ?", (rule_id,)).rowcount > 0
