"""The brain package: deterministic, rule-based transaction categorization."""

from .engine import categorize_one, categorize_statement  # noqa: F401
from .normalizer import normalize, strip_noise  # noqa: F401
