"""In-memory store for user-provided merchant overrides.

Maps a normalized merchant name -> category. Used by the classifier to
apply user corrections with confidence 1.0.
"""

from typing import Dict


class OverrideStore:
    """Thread-unsafe in-memory override store (sufficient for single-user app)."""

    def __init__(self) -> None:
        self._overrides: Dict[str, str] = {}

    def get(self, normalized_merchant: str) -> str | None:
        """Return the overridden category for a merchant, or None."""
        return self._overrides.get(normalized_merchant)

    def set(self, normalized_merchant: str, category: str) -> None:
        """Save a user override: normalized merchant -> category."""
        self._overrides[normalized_merchant] = category

    def remove(self, normalized_merchant: str) -> None:
        """Remove an override if it exists."""
        self._overrides.pop(normalized_merchant, None)

    def all(self) -> Dict[str, str]:
        """Return a copy of all overrides."""
        return dict(self._overrides)

    def clear(self) -> None:
        """Remove all overrides (mainly for testing)."""
        self._overrides.clear()
