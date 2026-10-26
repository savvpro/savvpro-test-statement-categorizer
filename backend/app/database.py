"""Small transactional SQLite store. No destructive startup migrations."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "ledgerlens.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS statements (
    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
    currency TEXT NOT NULL, options_json TEXT NOT NULL, row_count INTEGER NOT NULL,
    blank_rows INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY, statement_id TEXT NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    source_row INTEGER NOT NULL, date TEXT NOT NULL, description TEXT NOT NULL,
    normalized TEXT NOT NULL, amount_minor INTEGER NOT NULL,
    decision_json TEXT NOT NULL, kind TEXT NOT NULL, category TEXT NOT NULL,
    reviewed INTEGER NOT NULL DEFAULT 0, duplicate_group TEXT,
    duplicate_status TEXT NOT NULL DEFAULT 'none', version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS transactions_statement ON transactions(statement_id, source_row);
CREATE TABLE IF NOT EXISTS review_events (
    id INTEGER PRIMARY KEY, transaction_id TEXT NOT NULL
    REFERENCES transactions(id) ON DELETE CASCADE,
    action TEXT NOT NULL, before_json TEXT NOT NULL, after_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
PRAGMA user_version = 1;
"""


def db_path() -> Path:
    return Path(os.environ.get("LEDGERLENS_DB", str(DEFAULT_PATH)))


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize():
    with connect() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            raise RuntimeError("Database schema is newer than this application.")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)


@contextmanager
def read_snapshot():
    """Keep related reads on one SQLite snapshot, even while another tab commits an edit."""
    with connect() as conn:
        conn.execute("BEGIN")
        yield conn
