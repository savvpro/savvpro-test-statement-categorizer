"""Description normalization for the categorization brain.

Pipeline:
  1. Uppercase
  2. Strip noisy prefixes (SQ *, PAYPAL *, AMZN MKTP US*, POS, PURCHASE, etc.)
  3. Strip trailing store/reference numbers
  4. Collapse whitespace
"""

import re

from app.brain.constants import NOISY_PREFIXES


def normalize(description: str) -> str:
    """Normalize a raw merchant description into a canonical form.

    Args:
        description: Raw description string from the statement.

    Returns:
        Normalized uppercase string, or empty string if blank.
    """
    if not description or not description.strip():
        return ""

    text = description.upper().strip()

    # Remove noisy prefixes (loop until none match)
    changed = True
    while changed:
        changed = False
        for prefix in NOISY_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                changed = True
                break

    # Strip trailing store/reference numbers (e.g. "#1234" or long digit runs)
    text = re.sub(r"\s+#\d+\s*$", "", text)
    text = re.sub(r"\s+\d{6,}\s*$", "", text)

    # Collapse internal whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
