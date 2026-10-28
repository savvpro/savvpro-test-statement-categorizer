"""Combine candidates into one decision. This is where the brain decides it is not sure."""

from collections import defaultdict

from app.brain import explain
from app.brain.context import BrainSettings
from app.brain.state import RowState
from app.domain.enums import NON_BLOCKING_FLAGS, Category, CategoryKind, Direction, Flag, Status
from app.domain.models import Candidate, Decision
from app.domain.taxonomy import info, is_allowed

MAX_CONFIDENCE = 0.99
CAPITAL_CATEGORIES = frozenset({Category.REPAIRS, Category.SUPPLIES, Category.CLEANING_MAINTENANCE})


def treat_as_refund(state: RowState, category: Category) -> bool:
    """An expense category on an inflow is valid only as a refund, with evidence."""
    if state.is_refund:
        return True
    return (
        state.direction is Direction.INFLOW
        and info(category).kind is CategoryKind.EXPENSE
        and state.refund_evidence
    )


def allowed_candidates(state: RowState) -> list[Candidate]:
    return [
        c
        for c in state.candidates
        if is_allowed(c.category, state.direction, is_refund=treat_as_refund(state, c.category))
    ]


def aggregate(candidates: list[Candidate]) -> list[tuple[Category, float]]:
    """Noisy-OR per category: agreeing independent evidence raises confidence."""
    miss: dict[Category, float] = defaultdict(lambda: 1.0)
    for c in candidates:
        miss[c.category] *= 1.0 - c.score
    ranked = [(cat, min(MAX_CONFIDENCE, 1.0 - m)) for cat, m in miss.items()]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def preliminary_top(state: RowState) -> Category | None:
    ranked = aggregate(allowed_candidates(state))
    return ranked[0][0] if ranked else None


def resolve(state: RowState, settings: BrainSettings) -> Decision:
    txn = state.txn
    flags = set(state.flags)

    if state.is_duplicate:
        dup_reasons = tuple(
            explain.FLAG_TEXT[f] for f in sorted(flags) if f.name.startswith("DUPLICATE")
        )
        return Decision(
            category=None,
            status=Status.DUPLICATE,
            confidence=1.0,
            reasons=dup_reasons,
            rule_ids=("duplicate",),
            flags=frozenset(flags),
            duplicate_of_row=state.duplicate_of_row,
        )

    allowed = allowed_candidates(state)
    if state.candidates and not allowed:
        flags.add(Flag.DIRECTION_CONFLICT)
    ranked = aggregate(allowed)

    if not ranked:
        if not flags - NON_BLOCKING_FLAGS:
            flags.add(Flag.UNKNOWN_MERCHANT)
        return Decision(
            category=None,
            status=Status.NEEDS_REVIEW,
            confidence=0.0,
            reasons=tuple(explain.FLAG_TEXT[f] for f in sorted(flags)) + tuple(state.extra_reasons),
            rule_ids=(),
            flags=frozenset(flags),
        )

    top, top_p = ranked[0]
    second_p = ranked[1][1] if len(ranked) > 1 else 0.0
    is_refund = treat_as_refund(state, top) and (
        txn.direction is Direction.INFLOW or top is Category.RENT
    )

    if (
        top in CAPITAL_CATEGORIES
        and not is_refund
        and abs(txn.amount_cents) >= settings.de_minimis_cents
    ):
        flags.add(Flag.POSSIBLE_CAPITAL_IMPROVEMENT)
    if top_p >= settings.auto_threshold and top_p - second_p < settings.margin_threshold:
        flags.add(Flag.AMBIGUOUS_MATCH)

    blocking = flags - NON_BLOCKING_FLAGS
    confident = top_p >= settings.auto_threshold and top_p - second_p >= settings.margin_threshold
    status = Status.AUTO if confident and not blocking else Status.NEEDS_REVIEW

    top_candidates = [c for c in allowed if c.category is top]
    reasons = [c.reason for c in sorted(top_candidates, key=lambda c: c.score, reverse=True)]
    if is_refund and txn.direction is Direction.INFLOW:
        reasons.append(
            f"Money returned by the merchant reduces {explain.label(top)}. It is not income."
        )
    reasons.extend(state.extra_reasons)
    reasons.extend(explain.FLAG_TEXT[f] for f in sorted(flags))
    if status is Status.NEEDS_REVIEW and top_p < settings.auto_threshold:
        reasons.append(explain.low_confidence(top, top_p))

    return Decision(
        category=top if status is Status.AUTO else None,
        status=status,
        confidence=round(top_p, 2),
        reasons=tuple(dict.fromkeys(reasons)),
        rule_ids=tuple(dict.fromkeys(c.rule_id for c in top_candidates)),
        flags=frozenset(flags),
        is_refund=is_refund,
        suggestion=top,
    )
