"""Description normalization service.

Provides deterministic normalization for transaction descriptions, handling whitespace,
case consistency, and empty values while preserving meaningful merchant tokens and punctuation.
"""

import re
from typing import Optional


def normalize_description(description: Optional[str]) -> str:
    """Normalize a raw transaction description for rule matching.

    Transformations performed:
    1. Handles None and empty inputs safely (returns empty string).
    2. Strips leading and trailing whitespace.
    3. Collapses consecutive whitespace (spaces, tabs, newlines) into a single space.
    4. Converts to uppercase for consistent case-insensitive rule matching.
    5. Preserves punctuation, domain names, and merchant identifiers without
       destructive stripping.

    Args:
        description: The original raw description string or None.

    Returns:
        The normalized uppercase description string.
    """
    if description is None:
        return ""

    # Strip leading and trailing whitespace
    stripped = description.strip()
    if not stripped:
        return ""

    # Collapse repeated whitespace (spaces, tabs, newlines) into a single space
    single_spaced = re.sub(r"\s+", " ", stripped)

    # Convert to uppercase for canonical matching
    return single_spaced.upper()
