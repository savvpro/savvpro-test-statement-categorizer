"""Stages 3-6: user memory, known merchants, keywords, fuzzy merchant match."""

from collections.abc import Mapping

from rapidfuzz import fuzz

from app.brain import explain
from app.brain.context import BrainSettings
from app.brain.rules import RuleSet
from app.brain.state import RowState
from app.domain.enums import Category, CategoryKind, Direction, Flag
from app.domain.taxonomy import info, is_allowed

MEMORY_SCORE = 0.98
FUZZY_DISCOUNT = 0.92


def memory(state: RowState, remembered: Mapping[str, Category]) -> None:
    category = remembered.get(state.txn.merchant_key)
    if category is None:
        return
    refund = state.refund_evidence and info(category).kind is CategoryKind.EXPENSE
    if not is_allowed(category, state.direction, is_refund=refund):
        return
    state.add(
        category, MEMORY_SCORE, "memory", "memory", explain.memory(state.txn.merchant_key, category)
    )
    state.memory_hit = True
    # The user has already decided how to treat this merchant or person.
    state.flags -= {Flag.MIXED_USE_MERCHANT, Flag.PAYMENT_TO_INDIVIDUAL}


def merchants(state: RowState, rules: RuleSet) -> None:
    key = state.txn.merchant_key
    for rule in rules.merchants:
        alias = next(
            (a for a, p in zip(rule.aliases, rule.alias_patterns, strict=True) if p.search(key)),
            None,
        )
        if alias is None:
            continue
        state.add(
            rule.category, rule.score, "merchant", rule.id, explain.merchant(alias, rule.category)
        )
        state.flags |= rule.flags
        state.merchant_hit = True


def keywords(state: RowState, rules: RuleSet) -> None:
    haystack = f"{state.txn.merchant_key} {(state.txn.memo or '').upper()}".strip()
    for rule in rules.keywords:
        # Keyword direction lists describe normal spending; inflows are judged as refunds later.
        if state.direction is Direction.OUTFLOW and Direction.OUTFLOW not in rule.directions:
            continue
        match = rule.pattern.search(haystack)
        if not match:
            continue
        state.add(
            rule.category,
            rule.score,
            "keyword",
            rule.id,
            explain.keyword(match.group(0), rule.category),
        )
        state.flags |= rule.flags


def fuzzy(state: RowState, rules: RuleSet, settings: BrainSettings) -> None:
    if state.merchant_hit or state.is_p2p or state.txn.channel == "CHECK":
        return
    key = state.txn.merchant_key
    if len(key) < 4:
        return
    best: tuple[float, str, int] | None = None
    for idx, rule in enumerate(rules.merchants):
        for alias in rule.aliases:
            if len(alias) < 4:
                continue
            ratio = float(fuzz.ratio(key, alias))
            if ratio >= settings.fuzzy_min_ratio and (best is None or ratio > best[0]):
                best = (ratio, alias, idx)
    if best is None:
        return
    ratio, alias, idx = best
    rule = rules.merchants[idx]
    score = rule.score * (ratio / 100) * FUZZY_DISCOUNT
    state.add(
        rule.category,
        score,
        "fuzzy",
        f"{rule.id}~fuzzy",
        explain.fuzzy(alias, ratio, rule.category),
    )
    state.flags |= rule.flags
