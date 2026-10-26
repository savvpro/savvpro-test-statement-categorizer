"""The brain: decides a category for one transaction, or says it is not sure.

Evidence is checked from strongest to weakest and the first tier that has something to
say wins:

1. the user's own past corrections for this merchant      (0.99)
2. a known merchant from the knowledge base               (0.70 - 0.96)
3. a generic keyword in the description                   (0.60 - 0.84)
4. a close misspelling of a known merchant                (0.70)
5. the category label the bank exported, if any           (0.60)

After that, sanity checks can only *lower* confidence: money flowing the wrong way for
the category, a suspicious amount, or conflicting evidence. Anything under the
threshold goes to Needs Review with the best guesses as suggestions.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher

from . import categories
from .categories import Kind
from .knowledge import (
    BANK_CATEGORY_HINTS,
    KEYWORD_RULES,
    MERCHANT_RULES,
    REFUND_MARKERS,
    Keyword,
    Rule,
)
from .models import Decision, Direction, Flag, Source, TransactionInput
from .normalize import normalize

DEFAULT_THRESHOLD = 0.75
FUZZY_MIN_RATIO = 0.84

UserRules = Mapping[tuple[str, str], str]  # (merchant_key, direction) -> category id


@dataclass(frozen=True, slots=True)
class _Match:
    rule: Rule
    span: tuple[int, int]

    @property
    def length(self) -> int:
        return self.span[1] - self.span[0]


@dataclass(frozen=True, slots=True)
class _KeywordMatch:
    keyword: Keyword
    span: tuple[int, int]
    text: str


def _money(amount: Decimal) -> str:
    return f"${abs(amount):,.2f}"


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


class Categorizer:
    def __init__(
        self,
        user_rules: UserRules | None = None,
        *,
        threshold: float = DEFAULT_THRESHOLD,
        rules: list[Rule] | None = None,
        keywords: list[Keyword] | None = None,
    ) -> None:
        self.user_rules = dict(user_rules or {})
        self.threshold = threshold
        self.rules = rules if rules is not None else MERCHANT_RULES
        self.keywords = keywords if keywords is not None else KEYWORD_RULES
        self._fuzzy_targets = [r for r in self.rules if r.fuzzy and not r.ambiguous]

    # ------------------------------------------------------------------ public API
    def categorize(self, tx: TransactionInput) -> Decision:
        norm = normalize(tx.description)
        direction = Direction.of(tx.amount)
        text = norm.text
        refund_marked = direction is Direction.IN and bool(REFUND_MARKERS.search(text))
        hint = BANK_CATEGORY_HINTS.get((tx.bank_category or "").strip().lower())

        d = Decision(
            merchant=text,
            merchant_key=norm.key,
            category=None,
            confidence=0.0,
            needs_review=False,
            source=Source.NONE,
        )
        matched_rule: Rule | None = None

        if user_category := self.user_rules.get((norm.key, direction.value)):
            d.category, d.confidence, d.source = user_category, 0.99, Source.USER_RULE
            d.reasons.append("You categorised this merchant before.")
        else:
            matched_rule = self._decide_from_evidence(d, text, direction, refund_marked, hint)

        if d.category:
            self._check_direction(d, direction, refund_marked, matched_rule)
        if d.category:
            self._check_amount(d, tx.amount, matched_rule)
        if d.category and d.confidence < self.threshold:
            d.send_to_review(
                f"Only {d.confidence:.0%} sure - asking instead of guessing.", cap=d.confidence
            )
        if not d.category:
            d.needs_review = True
        d.confidence = round(max(0.0, min(d.confidence, 0.99)), 2)
        d.suggestions = [s for i, s in enumerate(d.suggestions) if s not in d.suggestions[:i]]
        return d

    # ------------------------------------------------------------- evidence tiers
    def _decide_from_evidence(
        self,
        d: Decision,
        text: str,
        direction: Direction,
        refund_marked: bool,
        hint: str | None,
    ) -> Rule | None:
        match = self._match_rule(text, direction, refund_marked)
        keyword = self._match_keyword(text)

        if match and not match.rule.ambiguous:
            rule = match.rule
            d.category, d.confidence, d.source = (
                rule.category,
                rule.confidence,
                Source.KNOWLEDGE_BASE,
            )
            d.reasons.append(f"Recognised: {rule.name}. {rule.note}".strip())
            d.suggestions.extend(rule.suggestions)
            if hint == rule.category:
                d.confidence += 0.03
                d.reasons.append("Your bank's own category agrees.")
            if (
                keyword
                and keyword.keyword.category != rule.category
                and keyword.keyword.confidence >= 0.8
                and not _overlaps(keyword.span, match.span)
            ):
                d.suggestions.append(keyword.keyword.category)
                d.send_to_review(
                    f"Mixed signals: {rule.name} suggests "
                    f"{categories.get(rule.category).label}, but the description also says "
                    f"'{keyword.text}'."
                )
            return rule

        if match and match.rule.ambiguous:
            rule = match.rule
            d.source = Source.KNOWLEDGE_BASE
            if keyword and keyword.keyword.category in rule.suggestions:
                d.category, d.confidence = keyword.keyword.category, 0.8
                d.reasons.append(
                    f"{rule.name} sells many things, but the description says '{keyword.text}'."
                )
                return rule
            d.suggestions.extend(rule.suggestions)
            if hint:
                d.suggestions.insert(0, hint)
            d.flags.append(Flag.AMBIGUOUS_MERCHANT)
            d.reasons.append(f"{rule.name}: {rule.note}")
            if direction is Direction.IN and rule.direction is Direction.OUT:
                d.flags.append(Flag.REFUND)
                d.reasons.append("Money came back, so this is likely a refund. Which category?")
            return rule

        if keyword:
            kw = keyword.keyword
            d.category, d.confidence, d.source = kw.category, kw.confidence, Source.KEYWORD
            d.reasons.append(f"The description mentions '{keyword.text}'.")
            self._apply_hint(d, hint)
            return None

        if fuzzy := self._match_fuzzy(text, direction):
            rule, ratio = fuzzy
            d.category, d.confidence, d.source = rule.category, 0.7, Source.FUZZY
            d.reasons.append(f"Looks like a misspelling of '{rule.name}' ({ratio:.0%} similar).")
            self._apply_hint(d, hint)
            return None

        if hint:
            d.category, d.confidence, d.source = hint, 0.6, Source.BANK_CATEGORY
            d.reasons.append("Only your bank's own category label points to this.")
            return None

        if refund_marked:
            d.flags.append(Flag.REFUND)
            d.reasons.append("A refund from a merchant I don't recognise. Which category?")
        elif direction is Direction.IN:
            d.flags.append(Flag.UNKNOWN_DEPOSIT)
            d.reasons.append(
                "Unrecognised deposit. It is not counted as income until you confirm it."
            )
            d.suggestions.extend(["platform_income", "other_income", "transfer"])
        else:
            d.reasons.append("Unknown merchant - asking rather than guessing.")
        return None

    @staticmethod
    def _apply_hint(d: Decision, hint: str | None) -> None:
        if not hint:
            return
        if hint == d.category:
            d.confidence += 0.08
            d.reasons.append("Your bank's own category agrees.")
        else:
            d.confidence -= 0.1
            d.suggestions.append(hint)
            d.reasons.append("Your bank's own category disagrees.")

    # ----------------------------------------------------------------- matchers
    def _match_rule(self, text: str, direction: Direction, refund_marked: bool) -> _Match | None:
        same_direction: list[_Match] = []
        refund_candidates: list[_Match] = []
        for rule in self.rules:
            m = rule.pattern.search(text)
            if not m:
                continue
            match = _Match(rule, m.span())
            if rule.direction in (Direction.ANY, direction):
                same_direction.append(match)
            elif (
                # Money back from a merchant we normally pay: a refund candidate.
                direction is Direction.IN
                and rule.direction is Direction.OUT
                and (
                    rule.ambiguous
                    or categories.get(rule.category).kind in (Kind.EXPENSE, Kind.PERSONAL)
                )
            ):
                refund_candidates.append(match)

        groups = (
            (refund_candidates, same_direction)
            if refund_marked
            else (same_direction, refund_candidates)
        )
        for group in groups:
            if group:
                # Specific merchants beat ambiguous ones, then confidence, then longer match.
                return max(group, key=lambda m: (not m.rule.ambiguous, m.rule.confidence, m.length))
        return None

    def _match_keyword(self, text: str) -> _KeywordMatch | None:
        best: _KeywordMatch | None = None
        for kw in self.keywords:
            m = kw.pattern.search(text)
            if m and (best is None or kw.confidence > best.keyword.confidence):
                best = _KeywordMatch(kw, m.span(), m.group(0))
        return best

    def _match_fuzzy(self, text: str, direction: Direction) -> tuple[Rule, float] | None:
        words = re.findall(r"[A-Z0-9&']+", text)
        if not words:
            return None
        best: tuple[Rule, float] | None = None
        for rule in self._fuzzy_targets:
            if rule.direction not in (Direction.ANY, direction):
                continue
            n = len(rule.name.split())
            window = " ".join(words[:n])
            if len(window) < 4:
                continue
            ratio = SequenceMatcher(None, window, rule.name).ratio()
            if ratio >= FUZZY_MIN_RATIO and (best is None or ratio > best[1]):
                best = (rule, ratio)
        return best

    # ----------------------------------------------------------- sanity checks
    @staticmethod
    def _check_direction(
        d: Decision, direction: Direction, refund_marked: bool, rule: Rule | None
    ) -> None:
        kind = categories.get(d.category).kind
        label = categories.get(d.category).label
        if direction is Direction.IN and kind in (Kind.EXPENSE, Kind.PERSONAL):
            d.flags.append(Flag.REFUND)
            if refund_marked or (rule and rule.direction is Direction.IN):
                # Either the bank says "refund", or the rule was written for money coming
                # back (fee reversals, card rewards) - no reason to doubt it.
                d.reasons.append(f"Refund: money back reduces {label}. It is not income.")
            else:
                d.confidence -= 0.15
                d.reasons.append(
                    f"Money came back from a merchant you normally pay - treated as a refund "
                    f"that reduces {label}, not as income."
                )
        elif direction is Direction.OUT and kind is Kind.INCOME:
            d.send_to_review(
                "Money went out to an income platform - possibly a fee or clawback.",
                flag=Flag.DIRECTION_MISMATCH,
            )

    @staticmethod
    def _check_amount(d: Decision, amount: Decimal, rule: Rule | None) -> None:
        category = categories.get(d.category)
        if category.kind is not Kind.EXPENSE or amount > 0:
            return
        size = abs(amount)
        if category.max_typical_amount and size > category.max_typical_amount:
            d.send_to_review(
                f"{_money(amount)} is unusually large for {category.label} "
                f"(normally under ${category.max_typical_amount:,}).",
                flag=Flag.LARGE_AMOUNT,
            )
        elif (
            rule
            and d.source is Source.KNOWLEDGE_BASE
            and rule.min_typical_amount
            and size < rule.min_typical_amount
        ):
            d.suggestions.append("personal")
            d.send_to_review(
                f"Only {_money(amount)} at {rule.name} - could be snacks rather than fuel.",
                flag=Flag.SMALL_AMOUNT,
            )
