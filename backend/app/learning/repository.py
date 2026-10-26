"""Persistence for merchant rules learned from the user's corrections.

The engine depends only on the `MerchantRuleRepository` protocol, so the JSON
file store can be swapped for a database without touching categorization.
"""
import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Protocol

from ..domain.models import Category


@dataclass(frozen=True)
class MerchantRule:
    merchant: str
    category: Category


class MerchantRuleRepository(Protocol):
    def get(self, merchant: str) -> Optional[MerchantRule]: ...
    def list(self) -> List[MerchantRule]: ...
    def save(self, rule: MerchantRule) -> MerchantRule: ...
    def delete(self, merchant: str) -> bool: ...


class InMemoryMerchantRuleRepository:
    def __init__(self) -> None:
        self._rules: Dict[str, MerchantRule] = {}
        self._lock = threading.Lock()

    def get(self, merchant: str) -> Optional[MerchantRule]:
        return self._rules.get(merchant)

    def list(self) -> List[MerchantRule]:
        return sorted(self._rules.values(), key=lambda r: r.merchant)

    def save(self, rule: MerchantRule) -> MerchantRule:
        with self._lock:
            self._rules[rule.merchant] = rule
            self._persist()
        return rule

    def delete(self, merchant: str) -> bool:
        with self._lock:
            removed = self._rules.pop(merchant, None) is not None
            if removed:
                self._persist()
        return removed

    def _persist(self) -> None:
        """Hook for durable subclasses."""


class JsonFileMerchantRuleRepository(InMemoryMerchantRuleRepository):
    """Small-footprint durable store; writes are atomic (temp file + rename)."""

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = Path(path)
        if self._path.exists():
            for item in json.loads(self._path.read_text(encoding="utf-8")):
                rule = MerchantRule(merchant=item["merchant"], category=Category(item["category"]))
                self._rules[rule.merchant] = rule

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [{**asdict(r), "category": r.category.value} for r in self.list()]
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self._path)
