"""Duplicate detection: same date, same amount and same normalized merchant."""

from __future__ import annotations

from collections.abc import Hashable, Sequence


def find_duplicates(keys: Sequence[Hashable]) -> dict[int, int]:
    """Map index of each repeated row -> index of the first row it repeats.

    The first occurrence is kept as-is; only later copies are flagged.
    """
    first_seen: dict[Hashable, int] = {}
    duplicates: dict[int, int] = {}
    for index, key in enumerate(keys):
        if key in first_seen:
            duplicates[index] = first_seen[key]
        else:
            first_seen[key] = index
    return duplicates
