from app.brain.models import Candidate, SignalSource
from app.brain.signals import SCORES, RowContext


def user_rule_signal(ctx: RowContext, user_rules: dict[str, str]) -> list[Candidate]:
    category = user_rules.get(ctx.key)
    if category is None:
        return []
    return [
        Candidate(
            category,
            SCORES["user_rule"],
            f"you categorized '{ctx.key}' as {category} before",
            SignalSource.user_rule,
            f"user:{ctx.key}",
        )
    ]
