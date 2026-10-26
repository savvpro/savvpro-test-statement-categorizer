"""Central configuration: paths, thresholds and shared constants.

Everything the brain uses to make decisions lives in app/data/rules.json
so categories can be tuned without touching code.
"""

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = APP_DIR / "data"
RULES_FILE = DATA_DIR / "rules.json"
SAMPLES_DIR = DATA_DIR / "samples"

# Built frontend (production mode: FastAPI serves the React app too)
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Confidence bands (see DESIGN.md, "Scoring")
#
#   confidence >= AUTO_CONFIDENCE      -> categorize silently          (high)
#   confidence >= CONFIRM_CONFIDENCE   -> categorize BUT ask to confirm (medium)
#   confidence <  CONFIRM_CONFIDENCE   -> Needs Review, no category     (low)
#
# The task's one big rule: "A wrong guess is worse than asking."
# ---------------------------------------------------------------------------
AUTO_CONFIDENCE = 0.80
CONFIRM_CONFIDENCE = 0.50

# If the runner-up category score is at least this fraction of the winner,
# the match is considered ambiguous and confidence gets dampened.
AMBIGUITY_RATIO = 0.80
AMBIGUITY_PENALTY = 0.75

# An explicit refund is anchored by the word itself, so we link it back to the
# original expense category on a weaker merchant match than we would require
# for auto-categorizing a spend.
REFUND_LINK_CONFIDENCE = 0.50

# Buckets that are never business spending (excluded from spending totals)
CATEGORY_TRANSFERS = "Transfers & Payments"
CATEGORY_INCOME = "Income"
CATEGORY_REFUNDS = "Refunds"
NON_SPENDING = {CATEGORY_TRANSFERS, CATEGORY_INCOME, CATEGORY_REFUNDS}

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
