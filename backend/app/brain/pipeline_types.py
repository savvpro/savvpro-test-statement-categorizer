"""Pipeline shared types – kept separate so stages don't import each other."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Proposal:
    """A single stage's proposed categorization for one row."""
    category: str
    confidence: float
    reason: str
    stage: str
    flags: list[str] = field(default_factory=list)
    linked_row_index: int | None = None
