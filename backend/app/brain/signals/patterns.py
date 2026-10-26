from app.brain.models import Candidate, SignalSource
from app.brain.rules import PatternRule
from app.brain.signals import SCORES, RowContext
from app.brain.signals.structural import match_rules


def pattern_signal(ctx: RowContext, rules: list[PatternRule]) -> list[Candidate]:
    return match_rules(ctx, rules, SignalSource.pattern, SCORES["pattern"], "pattern")
