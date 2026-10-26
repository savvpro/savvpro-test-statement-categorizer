"""Small local SQLite store, schema versioned and transactional."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def database():
    path = Path(os.environ.get("SORTEDHISAB_DB", ".local/sortedhisab.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
        INSERT OR IGNORE INTO schema_version VALUES (1);
        CREATE TABLE IF NOT EXISTS statements (
          id TEXT PRIMARY KEY, account TEXT NOT NULL, filename TEXT NOT NULL,
          digest TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(account, digest));
        CREATE TABLE IF NOT EXISTS transactions (
          id TEXT PRIMARY KEY, statement_id TEXT NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
          data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS rules (
          id TEXT PRIMARY KEY, account TEXT NOT NULL, match_text TEXT NOT NULL, data TEXT NOT NULL,
          UNIQUE(account, match_text));
        CREATE TABLE IF NOT EXISTS reviews (
          id INTEGER PRIMARY KEY, transaction_id TEXT NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
          previous_data TEXT NOT NULL, new_data TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        """)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def transactions(connection):
    return [
        json.loads(row["data"])
        for row in connection.execute("SELECT data FROM transactions ORDER BY rowid DESC")
    ]


def rules(connection, account=None):
    rows = connection.execute(
        "SELECT data FROM rules" + (" WHERE account = ?" if account else ""), (account,) if account else ()
    )
    return [json.loads(row["data"]) for row in rows]
