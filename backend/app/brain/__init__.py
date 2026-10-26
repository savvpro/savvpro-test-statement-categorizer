"""Rule-based categorisation engine. No machine-learning model or LLM is involved."""

from .engine import DEFAULT_THRESHOLD, Categorizer
from .models import Decision, Direction, Flag, Source, TransactionInput
from .normalize import normalize

__all__ = [
    "DEFAULT_THRESHOLD",
    "Categorizer",
    "Decision",
    "Direction",
    "Flag",
    "Source",
    "TransactionInput",
    "normalize",
]
