"""Loads and validates the rule set (app/data/rules.json).

The rule file is data, not code: adding a category or tweaking a keyword
weight never requires touching the engine.
"""

import json
from functools import lru_cache

from ..config import CATEGORY_INCOME, CATEGORY_REFUNDS, CATEGORY_TRANSFERS, RULES_FILE

SPECIAL_BUCKETS = [CATEGORY_TRANSFERS, CATEGORY_INCOME, CATEGORY_REFUNDS]


@lru_cache(maxsize=1)
def load_rules() -> dict:
    with open(RULES_FILE, encoding="utf-8") as f:
        rules = json.load(f)
    _validate(rules)
    return rules


def _validate(rules: dict) -> None:
    """Fail fast at startup if the rule file is malformed."""
    for cat in rules.get("spending_categories", []):
        if "name" not in cat or "keywords" not in cat:
            raise ValueError(f"Spending category missing name/keywords: {cat}")
        for entry in cat["keywords"]:
            if "kw" not in entry or "w" not in entry:
                raise ValueError(f"Keyword entry missing kw/w: {entry}")
            if not 0.0 <= float(entry["w"]) <= 1.0:
                raise ValueError(f"Keyword weight out of range [0,1]: {entry}")
    for bucket in ("transfers", "income", "refund"):
        if bucket not in rules.get("special", {}):
            raise ValueError(f"Special flow '{bucket}' missing from rules file")


def spending_categories() -> list[dict]:
    return load_rules()["spending_categories"]


def special_keywords(bucket: str) -> list[dict]:
    return load_rules()["special"][bucket]["keywords"]


def all_category_names() -> list[str]:
    names = [c["name"] for c in spending_categories()]
    return names + SPECIAL_BUCKETS


def rules_version() -> str:
    return load_rules().get("version", "unknown")
