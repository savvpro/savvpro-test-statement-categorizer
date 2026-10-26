import re

from app.brain.models import Candidate, SignalSource
from app.brain.signals import SCORES, RowContext


def keyword_signal(ctx: RowContext, keywords: dict[str, str]) -> list[Candidate]:
    seen: set[str] = set()
    candidates = []
    for word in re.findall(r"[A-Z]+", ctx.text):
        category = keywords.get(word)
        if category and category not in seen:
            seen.add(category)
            candidates.append(
                Candidate(
                    category,
                    SCORES["keyword"],
                    f"keyword '{word}'",
                    SignalSource.keyword,
                    f"keyword:{word}",
                )
            )
    return candidates
