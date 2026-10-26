"""The categorization engine: signals -> direction check -> aggregate -> decide.

Pure and deterministic. No DB, no web framework, no network, no AI models.
"""

import re
from dataclasses import dataclass, field

from app.brain.duplicates import mark_duplicates
from app.brain.models import (
    AccountType,
    Candidate,
    CategoryKind,
    Decision,
    ParsedRow,
    SignalSource,
    TxnStatus,
)
from app.brain.normalizer import merchant_key
from app.brain.refunds import link_refunds
from app.brain.rules import AmbiguousRule, Rules, load_rules
from app.brain.signals import RowContext
from app.brain.signals.fuzzy import fuzzy_signal
from app.brain.signals.keywords import keyword_signal
from app.brain.signals.merchants import merchant_signal
from app.brain.signals.patterns import pattern_signal
from app.brain.signals.recurring import recurring_months
from app.brain.signals.structural import structural_signal
from app.brain.signals.user_rules import user_rule_signal
from app.brain.taxonomy import NEEDS_REVIEW, Taxonomy, load_taxonomy


@dataclass(frozen=True, slots=True)
class Thresholds:
    auto_min: float = 0.80  # top score needed to auto-assign
    margin_min: float = 0.15  # top must beat the runner-up by this much
    agreement_bonus: float = 0.03  # 2+ independent sources agree on a category
    recurring_boost: float = 0.05  # same merchant + amount in 2+ months
    refund_window_days: int = 90


DEFAULT_THRESHOLDS = Thresholds()

# Non-operating categories that only make sense in one direction.
_CATEGORY_DIRECTION = {"refund": "in", "tax_payment": "out", "owner_draw": "out"}
# Sources strong enough to clear an ambiguous merchant (e.g. "AMAZON ... REFUND").
_OVERRIDES_AMBIGUITY = {SignalSource.user_rule, SignalSource.structural}


@dataclass(slots=True)
class _Scored:
    category_id: str
    score: float
    best: Candidate
    sources: set[SignalSource] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)


def direction_allows(category_id: str, direction: str | None, taxonomy: Taxonomy) -> bool:
    if direction is None:
        return True
    kind = taxonomy.get(category_id).kind
    if kind is CategoryKind.expense and direction == "in":
        return False
    if kind is CategoryKind.income and direction == "out":
        return False
    required = _CATEGORY_DIRECTION.get(category_id)
    return required is None or required == direction


def aggregate(candidates: list[Candidate], thresholds: Thresholds) -> list[_Scored]:
    by_category: dict[str, _Scored] = {}
    for c in candidates:
        scored = by_category.get(c.category_id)
        if scored is None:
            scored = by_category[c.category_id] = _Scored(c.category_id, c.score, c)
        elif c.score > scored.score:
            scored.score, scored.best = c.score, c
        scored.sources.add(c.source)
        scored.reasons.append(c.reason)
    for scored in by_category.values():
        if len(scored.sources) >= 2:
            scored.score += thresholds.agreement_bonus
            scored.reasons.append(f"{len(scored.sources)} independent signals agree")
    # Ties break on category id so results never depend on rule-file order.
    return sorted(by_category.values(), key=lambda s: (-s.score, s.category_id))


def _signals(ctx: RowContext, rules: Rules, user_rules: dict[str, str]) -> list[Candidate]:
    candidates = user_rule_signal(ctx, user_rules)
    candidates += structural_signal(ctx, rules.structural)
    merchant = merchant_signal(ctx, rules.merchants)
    candidates += merchant
    candidates += pattern_signal(ctx, rules.patterns)
    if not merchant:
        candidates += fuzzy_signal(ctx, rules.merchants)
    candidates += keyword_signal(ctx, rules.keywords)
    return candidates


def _ambiguous(text: str, rules: Rules) -> AmbiguousRule | None:
    return next((rule for rule in rules.ambiguous if rule.regex.search(text)), None)


def _review(key: str, reasons: list[str], suggested: str | None, confidence: float) -> Decision:
    return Decision(
        category_id=NEEDS_REVIEW,
        confidence=round(confidence, 3),
        status=TxnStatus.needs_review,
        merchant_key=key,
        reasons=reasons,
        suggested_category_id=suggested,
    )


def _decide_row(
    row: ParsedRow,
    key: str,
    recurring: int,
    account_type: AccountType,
    rules: Rules,
    taxonomy: Taxonomy,
    user_rules: dict[str, str],
    thresholds: Thresholds,
) -> Decision:
    direction = "in" if row.amount > 0 else "out" if row.amount < 0 else None
    text = re.sub(r"\s+", " ", row.description.upper()).strip()
    ctx = RowContext(text=text, key=key, direction=direction, account_type=account_type)

    candidates = _signals(ctx, rules, user_rules)
    kept = [c for c in candidates if direction_allows(c.category_id, direction, taxonomy)]
    dropped = sorted({c.category_id for c in candidates} - {c.category_id for c in kept})
    notes = [f"ignored {cat}: does not fit money {direction}" for cat in dropped]

    ranked = aggregate(kept, thresholds)
    if ranked and recurring:
        top = ranked[0]
        if taxonomy.get(top.category_id).kind is CategoryKind.expense:
            top.score += thresholds.recurring_boost
            top.reasons.append(f"recurring: same amount in {recurring} months")

    top = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None

    ambiguous = _ambiguous(text, rules)
    if ambiguous and (ambiguous.always or not any(c.source in _OVERRIDES_AMBIGUITY for c in kept)):
        decision = _review(
            key,
            [f"ambiguous: {ambiguous.reason}", *(top.reasons if top else []), *notes],
            ambiguous.suggest or (top.category_id if top else None),
            top.score if top else 0.0,
        )
        decision.flags.append("ambiguous")
        if ambiguous.id == "chargeback":
            decision.flags.append("chargeback")
        decision.rule_id = f"ambiguous:{ambiguous.id}"
        return decision

    if top is None:
        return _review(key, ["no match: no rule or known merchant fits", *notes], None, 0.0)

    margin = top.score - (second.score if second else 0.0)
    if top.score >= thresholds.auto_min and margin >= thresholds.margin_min:
        return Decision(
            category_id=top.category_id,
            confidence=round(min(top.score, 1.0), 3),
            status=TxnStatus.auto,
            merchant_key=key,
            reasons=[*top.reasons, *notes],
            rule_id=top.best.rule_id,
        )

    if second and margin < thresholds.margin_min:
        reason = f"conflict: {top.category_id} vs {second.category_id}"
    else:
        reason = f"low confidence: best guess {top.category_id} ({top.best.source.value})"
    decision = _review(key, [reason, *top.reasons, *notes], top.category_id, top.score)
    decision.rule_id = top.best.rule_id
    return decision


def categorize(
    rows: list[ParsedRow],
    account_type: AccountType,
    user_rules: dict[str, str] | None = None,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
) -> list[Decision]:
    rules = load_rules()
    taxonomy = load_taxonomy()
    learned = {k.upper(): v for k, v in (user_rules or {}).items()}
    for category_id in learned.values():
        if category_id not in taxonomy or category_id == NEEDS_REVIEW:
            raise ValueError(f"user rule points at invalid category {category_id!r}")

    keys = [merchant_key(row.description) for row in rows]
    recurring = recurring_months(rows, keys)
    decisions = [
        _decide_row(row, key, rec, account_type, rules, taxonomy, learned, thresholds)
        for row, key, rec in zip(rows, keys, recurring, strict=True)
    ]

    mark_duplicates(rows, decisions)
    link_refunds(rows, decisions, thresholds.refund_window_days)
    for row, decision in zip(rows, decisions, strict=True):
        if row.is_pending:
            decision.flags.append("pending")
    return decisions
