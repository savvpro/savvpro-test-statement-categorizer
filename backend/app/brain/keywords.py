"""
Stage 4 – Keyword and pattern rules.

Falls back here when the merchant dictionary has no match.
Loads regex patterns from keywords.yaml.
"""

from __future__ import annotations

import functools
import re

import yaml

from app.brain.normalize import NormalizedRow
from app.brain.pipeline_types import Proposal
from app.config import DATA_DIR

_KEYWORDS_PATH = DATA_DIR / "keywords.yaml"


@functools.lru_cache(maxsize=1)
def _load_keyword_rules() -> list[tuple[re.Pattern, str, float]]:
    """Return compiled (pattern, category, confidence) tuples."""
    with open(_KEYWORDS_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    rules: list[tuple[re.Pattern, str, float]] = []
    for entry in raw.get("rules", []):
        pat = re.compile(entry["pattern"], re.I)
        rules.append((pat, entry["category"], entry["confidence"]))
    return rules


def check_keywords(row: NormalizedRow) -> Proposal | None:
    """Apply keyword/pattern rules to the merchant_key and raw description."""
    rules = _load_keyword_rules()
    key = row.merchant_key
    raw = row.raw_description.upper()

    for pat, category, confidence in rules:
        if pat.search(key) or pat.search(raw):
            return Proposal(
                category=category,
                confidence=confidence,
                reason=f"Keyword match: {pat.pattern!r} → {category}",
                stage="keywords",
            )

    return None
