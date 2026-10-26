from app.brain.models import Candidate, SignalSource
from app.brain.signals import SCORES, RowContext


def find_merchant(key: str, merchants: dict[str, str]) -> str | None:
    """Exact key, or the longest known merchant that is a whole-word prefix of the key."""
    if key in merchants:
        return key
    words = key.split()
    for size in range(len(words) - 1, 0, -1):
        prefix = " ".join(words[:size])
        if prefix in merchants:
            return prefix
    return None


def merchant_signal(ctx: RowContext, merchants: dict[str, str]) -> list[Candidate]:
    name = find_merchant(ctx.key, merchants)
    if name is None:
        return []
    category = merchants[name]
    return [
        Candidate(
            category,
            SCORES["merchant"],
            f"known merchant '{name}'",
            SignalSource.merchant,
            f"merchant:{name}",
        )
    ]
