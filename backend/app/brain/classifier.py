from collections.abc import Sequence

from app.brain.models import Decision, UserRule
from app.brain.normalizer import normalize
from app.brain.rules import Rule, RuleSet, default_rules
from app.core.config import CARD_REFUND_CONFIDENCE, CONFIDENCE_THRESHOLD
from app.core.domain import NEEDS_REVIEW, Direction, Kind
from app.ingest.models import ParsedRow


def classify(
    row: ParsedRow,
    user_rules: Sequence[UserRule] = (),
    rules: RuleSet | None = None,
) -> Decision:
    """Decide the category of one row. Stages, first decisive match wins:
    user rules, structural, merchants, review, keywords, card-refund fallback, nothing."""
    rules = rules if rules is not None else default_rules()
    normalized = normalize(row.raw_description)

    if row.amount == 0:
        return Decision(
            category=NEEDS_REVIEW,
            kind="expense",
            confidence=0.0,
            rule_id=None,
            reason="amount is zero, nothing to categorize",
            needs_review=True,
        )
    direction: Direction = "in" if row.amount > 0 else "out"
    sign_kind: Kind = "income" if direction == "in" else "expense"

    for user_rule in user_rules:
        if normalized.merchant_key and user_rule.merchant_key == normalized.merchant_key:
            return Decision(
                category=user_rule.category,
                kind=user_rule.kind or sign_kind,
                confidence=1.0,
                rule_id=f"user:{user_rule.merchant_key}",
                reason="your saved rule for this merchant",
                needs_review=user_rule.category == NEEDS_REVIEW,
            )

    def applicable(section: list[Rule]) -> list[Rule]:
        return [r for r in section if r.applies_to(normalized.text, row.account_type, direction)]

    for section in (rules.structural, rules.merchants):
        hits = applicable(section)
        if hits:
            return _from_rule(hits[0], sign_kind)

    review_hits = applicable(rules.review)
    if review_hits:
        rule = review_hits[0]
        return Decision(
            category=NEEDS_REVIEW,
            kind=rule.kind or sign_kind,
            confidence=_confidence(rule),
            rule_id=rule.id,
            reason=rule.reason,
            needs_review=True,
            suggested_category=None if rule.category == NEEDS_REVIEW else rule.category,
        )

    keyword_hits = applicable(rules.keywords)
    if keyword_hits:
        if len({r.category for r in keyword_hits}) > 1:
            listed = ", ".join(f"{r.id} ({r.category})" for r in keyword_hits)
            return Decision(
                category=NEEDS_REVIEW,
                kind=sign_kind,
                confidence=0.0,
                rule_id="+".join(r.id for r in keyword_hits),
                reason=f"conflicting rules: {listed}",
                needs_review=True,
            )
        return _from_rule(max(keyword_hits, key=_confidence), sign_kind)

    if row.account_type == "card" and direction == "in":
        return Decision(
            category="Refund",
            kind="refund",
            confidence=CARD_REFUND_CONFIDENCE,
            rule_id="card_money_in",
            reason="money back from a merchant on a card",
            needs_review=CARD_REFUND_CONFIDENCE < CONFIDENCE_THRESHOLD,
        )

    return Decision(
        category=NEEDS_REVIEW,
        kind=sign_kind,
        confidence=0.0,
        rule_id=None,
        reason="no rule matched",
        needs_review=True,
    )


def _confidence(rule: Rule) -> float:
    return rule.confidence if rule.confidence is not None else 0.0


def _from_rule(rule: Rule, sign_kind: Kind) -> Decision:
    confidence = _confidence(rule)
    kind = rule.kind or sign_kind
    if confidence < CONFIDENCE_THRESHOLD:
        return Decision(
            category=NEEDS_REVIEW,
            kind=kind,
            confidence=confidence,
            rule_id=rule.id,
            reason=f"{rule.reason} (low confidence {confidence:.2f})",
            needs_review=True,
            suggested_category=rule.category,
        )
    return Decision(
        category=rule.category,
        kind=kind,
        confidence=confidence,
        rule_id=rule.id,
        reason=rule.reason,
        needs_review=False,
    )
