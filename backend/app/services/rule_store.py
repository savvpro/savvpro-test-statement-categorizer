import json
import logging
import os
import uuid
from datetime import datetime
from threading import RLock

from app.config import settings
from app.models.rule import CustomRule, RuleCreateRequest

logger = logging.getLogger(__name__)


class RuleStore:
    """Thread-safe persistent storage for user-defined categorization rules."""

    def __init__(self, storage_path: str | None = None):
        self.storage_path = storage_path or os.path.join(
            settings.data_dir, "user_rules.json"
        )
        self._lock = RLock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def get_all(self) -> list[CustomRule]:
        with self._lock:
            try:
                with open(self.storage_path, encoding="utf-8") as f:
                    data = json.load(f)
                    return [CustomRule(**item) for item in data]
            except Exception as e:
                logger.error("Failed to read user rules from %s: %s", self.storage_path, e)
                return []

    def add_rule(self, req: RuleCreateRequest) -> CustomRule:
        with self._lock:
            rules = self.get_all()

            # Check if active rule for exact pattern already exists; update it if so
            clean_pattern = req.pattern.strip().upper()
            existing = next(
                (r for r in rules if r.pattern.upper() == clean_pattern and r.is_active),
                None,
            )

            if existing:
                existing.category = req.category
                existing.notes = req.notes
                existing.rule_type = req.rule_type
                new_rule = existing
            else:
                new_rule = CustomRule(
                    id=f"rule_{uuid.uuid4().hex[:8]}",
                    pattern=clean_pattern,
                    category=req.category,
                    rule_type=req.rule_type,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    notes=req.notes,
                )
                rules.append(new_rule)

            # Persist to disk
            try:
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(
                        [r.model_dump(mode="json") for r in rules], f, indent=2
                    )
            except Exception as e:
                logger.error("Failed to save rules to %s: %s", self.storage_path, e)

            return new_rule

    def delete_rule(self, rule_id: str) -> bool:
        with self._lock:
            rules = self.get_all()
            filtered = [r for r in rules if r.id != rule_id]
            if len(filtered) == len(rules):
                return False

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(
                    [r.model_dump(mode="json") for r in filtered], f, indent=2
                )
            return True


rule_store = RuleStore()
