from rapidfuzz import fuzz, process

from app.brain.models import Candidate, SignalSource
from app.brain.signals import SCORES, RowContext

MIN_SET_RATIO = 90
# token_set_ratio scores a pure subset as 100 ("BEST" vs "BEST BUY"); a plain ratio floor
# stops one shared word from passing as a near-exact match.
MIN_PLAIN_RATIO = 80
MIN_KEY_LENGTH = 5


def fuzzy_signal(ctx: RowContext, merchants: dict[str, str]) -> list[Candidate]:
    if len(ctx.key) < MIN_KEY_LENGTH:
        return []
    match = process.extractOne(
        ctx.key, merchants.keys(), scorer=fuzz.token_set_ratio, score_cutoff=MIN_SET_RATIO
    )
    if match is None:
        return []
    name, ratio, _ = match
    if fuzz.ratio(ctx.key, name) < MIN_PLAIN_RATIO:
        return []
    low, high = SCORES["fuzzy_min"], SCORES["fuzzy_max"]
    score = round(low + (high - low) * (ratio - MIN_SET_RATIO) / (100 - MIN_SET_RATIO), 4)
    return [
        Candidate(
            merchants[name],
            score,
            f"looks like known merchant '{name}' ({ratio:.0f}% similar)",
            SignalSource.fuzzy,
            f"fuzzy:{name}",
        )
    ]
