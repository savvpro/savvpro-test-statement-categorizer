"""SQLite storage: statements, their transactions, and learned merchant rules."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    sign_mode TEXT NOT NULL,
    skipped TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learned_rules (
    merchant TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def db_path() -> Path:
    return Path(os.environ.get("CATEGORIZER_DB", Path(__file__).resolve().parents[2] / "data" / "app.db"))


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def learned_rules() -> dict[str, str]:
    with connect() as c:
        return {r["merchant"]: r["category"] for r in c.execute("SELECT merchant, category FROM learned_rules")}


def remember(merchant: str, category: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO learned_rules(merchant, category, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(merchant) DO UPDATE SET category = excluded.category, updated_at = excluded.updated_at",
            (merchant, category, _now()),
        )


def save_statement(filename: str, sign_mode: str, skipped: list[dict], items: list[dict]) -> int:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO statements(filename, uploaded_at, sign_mode, skipped) VALUES (?, ?, ?, ?)",
            (filename, _now(), sign_mode, json.dumps(skipped)),
        )
        sid = cur.lastrowid
        c.executemany(
            "INSERT INTO transactions(statement_id, data) VALUES (?, ?)", [(sid, json.dumps(it)) for it in items]
        )
        return sid


def list_statements() -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT s.id, s.filename, s.uploaded_at, COUNT(t.id) AS transactions FROM statements s "
            "LEFT JOIN transactions t ON t.statement_id = s.id GROUP BY s.id ORDER BY s.id DESC"
        )
        return [dict(r) for r in rows]


def get_statement(statement_id: int) -> tuple[dict, list[dict]] | None:
    with connect() as c:
        s = c.execute("SELECT * FROM statements WHERE id = ?", (statement_id,)).fetchone()
        if s is None:
            return None
        items = [
            {"id": r["id"], **json.loads(r["data"])}
            for r in c.execute("SELECT id, data FROM transactions WHERE statement_id = ? ORDER BY id", (statement_id,))
        ]
        meta = dict(s)
        meta["skipped"] = json.loads(meta["skipped"])
        return meta, items


def update_transactions(updates: dict[int, dict]) -> None:
    with connect() as c:
        c.executemany(
            "UPDATE transactions SET data = ? WHERE id = ?",
            [(json.dumps({k: v for k, v in data.items() if k != "id"}), tid) for tid, data in updates.items()],
        )


def statement_of(transaction_id: int) -> int | None:
    with connect() as c:
        r = c.execute("SELECT statement_id FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        return r["statement_id"] if r else None


def delete_statement(statement_id: int) -> bool:
    with connect() as c:
        return c.execute("DELETE FROM statements WHERE id = ?", (statement_id,)).rowcount > 0
