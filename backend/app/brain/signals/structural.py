from app.brain.models import Candidate, SignalSource
from app.brain.rules import PatternRule
from app.brain.signals import SCORES, RowContext


def match_rules(
    ctx: RowContext, rules: list[PatternRule], source: SignalSource, score: float, label: str
) -> list[Candidate]:
    return [
        Candidate(rule.category, score, f"{label} '{rule.id}'", source, f"{source.value}:{rule.id}")
        for rule in rules
        if rule.applies(ctx.text, ctx.direction, ctx.account_type)
    ]


def structural_signal(ctx: RowContext, rules: list[PatternRule]) -> list[Candidate]:
    return match_rules(ctx, rules, SignalSource.structural, SCORES["structural"], "structural rule")
