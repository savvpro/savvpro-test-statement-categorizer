"""Confidence scoring and manual review policy.

Provides rule-based confidence calculations, configurable review thresholds,
and confidence score clamping [0.0, 1.0].
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ConfidenceLevel:
    """Predefined rule-based confidence score constants."""

    HIGH_SPECIFIC: float = 0.95       # Exact / specific trusted merchant with consistent direction
    STRONG_PATTERN: float = 0.85      # Recognized pattern (e.g., standard hosting/software indicator)
    MODERATE: float = 0.70            # Plausible match with incomplete certainty (e.g. general transfer)
    AMBIGUOUS: float = 0.30           # Multi-category merchant requiring human clarification
    VERY_LOW: float = 0.10            # Weak signal
    UNKNOWN: float = 0.00             # No rule matched or empty description


# Default threshold: transactions with confidence below 0.80 require manual review.
DEFAULT_REVIEW_THRESHOLD: float = 0.80


def evaluate_confidence(
    base_score: float,
    force_review: bool = False,
    threshold: float = DEFAULT_REVIEW_THRESHOLD,
) -> Tuple[float, bool]:
    """Evaluate final confidence score and review requirement.

    Scores are strictly clamped between 0.0 and 1.0.
    A transaction requires review if force_review is True OR if the confidence score
    falls strictly below the review threshold.

    Args:
        base_score: Raw confidence score assigned by the rule.
        force_review: Explicit flag to mandate manual review regardless of score.
        threshold: The threshold at or above which a transaction does not require review.

    Returns:
        A tuple of (clamped_confidence_score, review_required).
    """
    clamped = max(0.0, min(1.0, float(base_score)))
    # If clamped score is strictly below the threshold, or force_review is requested,
    # manual review is required.
    review_required = force_review or (clamped < threshold)
    return round(clamped, 4), review_required
