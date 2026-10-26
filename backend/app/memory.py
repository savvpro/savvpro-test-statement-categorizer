"""Saved merchant decisions. This is a lookup table, not a model."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class Memory:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS merchant_rules (
                    fingerprint TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def get(self, fingerprint: str) -> str | None:
        if not fingerprint:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT category FROM merchant_rules WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()
        return None if row is None else str(row[0])

    def put(self, fingerprint: str, category: str) -> None:
        if not fingerprint:
            return
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO merchant_rules (fingerprint, category, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    category = excluded.category,
                    updated_at = excluded.updated_at
                """,
                (fingerprint, category, now),
            )

    def as_dict(self) -> dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT fingerprint, category FROM merchant_rules").fetchall()
        return {str(fingerprint): str(category) for fingerprint, category in rows}

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection
