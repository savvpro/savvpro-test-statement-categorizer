"""Unit tests for confidence scoring and review threshold evaluations."""

import pytest
from app.services.confidence import (
    DEFAULT_REVIEW_THRESHOLD,
    ConfidenceLevel,
    evaluate_confidence,
)


def test_confidence_scores_clamped_between_zero_and_one():
    """Ensure confidence values below 0.0 or above 1.0 are strictly clamped."""
    score_low, _ = evaluate_confidence(-0.5)
    assert score_low == 0.0

    score_high, _ = evaluate_confidence(1.75)
    assert score_high == 1.0

    score_normal, _ = evaluate_confidence(0.85)
    assert score_normal == 0.85


def test_confidence_threshold_boundary_behavior():
    """Verify review recommendations at, strictly below, and strictly above the threshold."""
    threshold = 0.80

    # Below threshold -> review required
    score_below, review_below = evaluate_confidence(0.79, threshold=threshold)
    assert score_below == 0.79
    assert review_below is True

    # Exactly at threshold -> no review required
    score_at, review_at = evaluate_confidence(0.80, threshold=threshold)
    assert score_at == 0.80
    assert review_at is False

    # Above threshold -> no review required
    score_above, review_above = evaluate_confidence(0.81, threshold=threshold)
    assert score_above == 0.81
    assert review_above is False


def test_forced_review_overrides_high_score():
    """Verify that force_review=True requires review even with high confidence score."""
    score, review = evaluate_confidence(0.98, force_review=True, threshold=0.80)
    assert score == 0.98
    assert review is True


def test_predefined_confidence_hierarchy():
    """Verify that trusted specific matches rank higher than ambiguous/unknown matches."""
    assert ConfidenceLevel.HIGH_SPECIFIC > ConfidenceLevel.STRONG_PATTERN
    assert ConfidenceLevel.STRONG_PATTERN > ConfidenceLevel.MODERATE
    assert ConfidenceLevel.MODERATE > ConfidenceLevel.AMBIGUOUS
    assert ConfidenceLevel.AMBIGUOUS > ConfidenceLevel.UNKNOWN
    assert ConfidenceLevel.UNKNOWN == 0.0


def test_configurable_threshold_override():
    """Verify that callers can supply a custom review threshold."""
    # With a strict 0.90 threshold, an 0.85 score now requires review
    _, review = evaluate_confidence(0.85, threshold=0.90)
    assert review is True

    # With a relaxed 0.60 threshold, a 0.70 score does not require review
    _, review_relaxed = evaluate_confidence(0.70, threshold=0.60)
    assert review_relaxed is False
