"""
Stage 3 – Merchant dictionary lookup (exact and fuzzy).

Loads the YAML dictionary once, builds a lookup table, and provides
exact match plus RapidFuzz token_set_ratio fallback.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml
from rapidfuzz import fuzz

from app.brain.normalize import NormalizedRow
from app.brain.pipeline_types import Proposal
from app.config import (
    CONFIDENCE_DICT_EXACT,
    CONFIDENCE_DICT_FUZZY_MAX,
    CONFIDENCE_DICT_FUZZY_MIN,
    CONFIDENCE_MIXED_MERCHANT_CAP,
    DATA_DIR,
    FUZZY_MATCH_THRESHOLD,
)

_MERCHANTS_PATH = DATA_DIR / "merchants.yaml"


@functools.lru_cache(maxsize=1)
def _load_merchant_dict() -> tuple[dict[str, str], set[str]]:
    """
    Returns (merchant_key → category, mixed_use_set).

    Cached so the YAML is read only once per process.
    """
    with open(_MERCHANTS_PATH, "r", encoding="utf-8") as f:
        raw: dict[str, list[str]] = yaml.safe_load(f) or {}

    lookup: dict[str, str] = {}
    mixed: set[str] = set()

    for category, merchants in raw.items():
        if category == "_mixed_use":
            for m in merchants:
                mixed.add(m.upper().strip())
            continue
        for m in merchants:
            key = m.upper().strip()
            lookup[key] = category

    return lookup, mixed


def check_dictionary(row: NormalizedRow) -> Proposal | None:
    """Exact or fuzzy match against the curated merchant dictionary."""
    lookup, mixed_use = _load_merchant_dict()
    key = row.merchant_key.strip()
    if not key:
        return None

    # ── Exact match ──────────────────────────────────────────────────────
    if key in lookup:
        is_mixed = key in mixed_use
        conf = CONFIDENCE_MIXED_MERCHANT_CAP if is_mixed else CONFIDENCE_DICT_EXACT
        flags = ["mixed_use_merchant"] if is_mixed else []
        return Proposal(
            category=lookup[key],
            confidence=conf,
            reason=f"Merchant dictionary exact match: {key} → {lookup[key]}",
            stage="dictionary",
            flags=flags,
        )

    # Check mixed-use exact match (these aren't in lookup, just in the set)
    if key in mixed_use:
        # Default to office_supplies for mixed-use – will be reviewed
        return Proposal(
            category="office_supplies",
            confidence=CONFIDENCE_MIXED_MERCHANT_CAP,
            reason=f"Mixed-use merchant: {key} – needs review for business purpose",
            stage="dictionary",
            flags=["mixed_use_merchant"],
        )

    # ── Fuzzy match ──────────────────────────────────────────────────────
    best_score = 0.0
    best_key = ""
    best_cat = ""

    for dict_key, cat in lookup.items():
        score = fuzz.token_set_ratio(key, dict_key)
        if score > best_score:
            best_score = score
            best_key = dict_key
            best_cat = cat

    if best_score >= FUZZY_MATCH_THRESHOLD:
        # Scale confidence linearly between fuzzy min and max
        ratio = (best_score - FUZZY_MATCH_THRESHOLD) / (100 - FUZZY_MATCH_THRESHOLD)
        conf = CONFIDENCE_DICT_FUZZY_MIN + ratio * (
            CONFIDENCE_DICT_FUZZY_MAX - CONFIDENCE_DICT_FUZZY_MIN
        )
        is_mixed = best_key in mixed_use
        if is_mixed:
            conf = min(conf, CONFIDENCE_MIXED_MERCHANT_CAP)
        return Proposal(
            category=best_cat,
            confidence=round(conf, 2),
            reason=f"Merchant dictionary fuzzy match: {key} ≈ {best_key} ({best_score:.0f}%) → {best_cat}",
            stage="dictionary",
            flags=["mixed_use_merchant"] if is_mixed else [],
        )

    return None
