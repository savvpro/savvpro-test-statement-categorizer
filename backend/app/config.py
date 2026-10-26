"""Configuration module – all tunables in one place."""

from __future__ import annotations

import os
from pathlib import Path


# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR.parent / "instance"

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DB_DIR / 'taxsort.db'}",
)

# ── Brain thresholds ─────────────────────────────────────────────────────────
CONFIDENCE_AUTO = 0.85          # >= this → auto-categorized
CONFIDENCE_SUGGESTED = 0.60     # >= this but < auto → suggested (pre-filled, highlighted)
# below CONFIDENCE_SUGGESTED → needs_review

# Stage-specific confidences
CONFIDENCE_USER_RULE = 0.98
CONFIDENCE_DICT_EXACT = 0.95
CONFIDENCE_DICT_FUZZY_MIN = 0.80
CONFIDENCE_DICT_FUZZY_MAX = 0.90
CONFIDENCE_KEYWORD = 0.75
CONFIDENCE_KEYWORD_LOW = 0.60
CONFIDENCE_REFUND = 0.92
CONFIDENCE_INCOME = 0.80
CONFIDENCE_MIXED_MERCHANT_CAP = 0.50

# Scoring adjustments
CONFLICT_PENALTY = 0.25
OUTLIER_PENALTY = 0.10
OUTLIER_MULTIPLIER = 5.0        # amount > median * this → outlier

# ── Transfer pairing ────────────────────────────────────────────────────────
TRANSFER_PAIR_DAYS = 3          # max days apart for paired-match detection

# ── Refund matching ─────────────────────────────────────────────────────────
REFUND_LOOKBACK_DAYS = 90

# ── Large purchase threshold ────────────────────────────────────────────────
LARGE_PURCHASE_CENTS = 250_000  # $2,500

# ── Fuzzy matching ──────────────────────────────────────────────────────────
FUZZY_MATCH_THRESHOLD = 90      # RapidFuzz token_set_ratio threshold

# ── Upload ──────────────────────────────────────────────────────────────────
UPLOAD_DIR = DB_DIR / "uploads"
MAX_UPLOAD_SIZE_MB = 20
