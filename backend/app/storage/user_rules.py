"""Rules learned from the user's corrections, kept in a small JSON file."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from app.brain.categories import CATEGORIES


class UserRuleStore:
    """Maps a merchant key to a category id. Safe to share between request threads."""

    def __init__(self, path: Path | None = None):
        self._path = path
        self._lock = threading.Lock()
        self._rules: dict[str, str] = {}
        if path is not None:
            self._rules = self._load(path)

    @staticmethod
    def _load(path: Path) -> dict[str, str]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {k: v for k, v in raw.items() if isinstance(k, str) and v in CATEGORIES}

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._rules.get(key)

    def set(self, key: str, category_id: str) -> None:
        if not key.strip():
            return
        with self._lock:
            self._rules[key] = category_id
            self._persist()

    def all(self) -> dict[str, str]:
        with self._lock:
            return dict(self._rules)

    def _persist(self) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._rules, handle, indent=2, sort_keys=True)
            os.replace(tmp, self._path)
        except OSError:
            # Keep working in memory if the disk is read-only; the rule still applies this run.
            pass
