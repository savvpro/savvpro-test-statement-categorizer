"""SQLite persistence. One short-lived connection per unit of work."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS statements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filename        TEXT NOT NULL,
    uploaded_at     TEXT NOT NULL,
    file_format     TEXT NOT NULL,
    sign_convention TEXT NOT NULL,
    warnings        TEXT NOT NULL DEFAULT '[]',
    skipped         TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_id    INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    line            INTEGER NOT NULL,
    date            TEXT NOT NULL,
    description     TEXT NOT NULL,
    merchant        TEXT NOT NULL,
    merchant_key    TEXT NOT NULL,
    amount_cents    INTEGER NOT NULL,
    direction       TEXT NOT NULL,
    bank_category   TEXT,
    category        TEXT,
    status          TEXT NOT NULL,          -- auto | needs_review | reviewed
    confidence      REAL NOT NULL,
    source          TEXT NOT NULL,
    reasons         TEXT NOT NULL DEFAULT '[]',
    suggestions     TEXT NOT NULL DEFAULT '[]',
    flags           TEXT NOT NULL DEFAULT '[]',
    engine_category TEXT                    -- what the brain chose, kept for auditing
);
CREATE INDEX IF NOT EXISTS ix_tx_statement ON transactions(statement_id);
CREATE INDEX IF NOT EXISTS ix_tx_fingerprint ON transactions(date, amount_cents, description);

CREATE TABLE IF NOT EXISTS user_rules (
    merchant_key TEXT NOT NULL,
    direction    TEXT NOT NULL,
    category     TEXT NOT NULL,
    example      TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (merchant_key, direction)
);
"""


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
