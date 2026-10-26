"""Run a parsed statement through the brain and produce finished transactions."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.brain.categories import CATEGORIES, NEEDS_REVIEW
from app.brain.classifier import Classifier, Decision
from app.brain.direction import choose_convention, spend_amount
from app.brain.normalize import Normalized
from app.config import Settings
from app.domain.models import (
    Convention,
    Flag,
    Kind,
    ParsedStatement,
    RawRow,
    Status,
    Transaction,
)


@dataclass
class _Draft:
    index: int
    row: RawRow
    spend: Decimal
    currency: str
    norm: Normalized
    decision: Decision
    refund_of: int | None = None
    extra_reasons: list[str] = field(default_factory=list)
    extra_flags: list[Flag] = field(default_factory=list)

    @property
    def txn_id(self) -> str:
        return make_id(self.index)


def make_id(index: int) -> str:
    return f"t-{index + 1:04d}"


@dataclass(frozen=True)
class Categorized:
    transactions: list[Transaction]
    convention: Convention
    currency: str
    warnings: list[str]


def categorize(
    parsed: ParsedStatement,
    classifier: Classifier,
    settings: Settings,
    requested_convention: Convention | None = None,
) -> Categorized:
    convention, warnings = choose_convention(
        parsed.rows, requested=requested_convention, hint=parsed.convention_hint
    )
    currency = _statement_currency(parsed, settings)

    drafts: list[_Draft] = []
    for index, row in enumerate(parsed.rows):
        spend = spend_amount(row, convention)
        decision, norm = classifier.classify(row.description, money_in=spend < 0)
        drafts.append(_Draft(index, row, spend, row.currency or currency, norm, decision))

    _match_refunds(drafts)
    _flag_duplicates(drafts, warnings)
    transactions = [_finalize(d, convention, currency, settings) for d in drafts]
    return Categorized(transactions, convention, currency, warnings)


def _statement_currency(parsed: ParsedStatement, settings: Settings) -> str:
    if parsed.currency_hint:
        return parsed.currency_hint
    counts = Counter(r.currency for r in parsed.rows if r.currency)
    if counts:
        return counts.most_common(1)[0][0]
    return settings.default_currency


# -- refunds ---------------------------------------------------------------------------------


def _same_merchant(a: Normalized, b: Normalized) -> bool:
    """Equal keys, or one is a leading part of the other (ADOBE vs ADOBE CREATIVE CLOUD)."""
    ta, tb = a.key.split(), b.key.split()
    if not ta or not tb:
        return False
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return long_[: len(short)] == short


def _match_refunds(drafts: list[_Draft]) -> None:
    purchases = [d for d in drafts if d.spend > 0]
    remaining = {d.index: d.spend for d in purchases}

    for refund in (d for d in drafts if d.decision.refund_candidate):
        amount = -refund.spend
        candidates = [
            p
            for p in purchases
            if p.currency == refund.currency
            and p.row.date <= refund.row.date + timedelta(days=1)
            and _same_merchant(p.norm, refund.norm)
            and remaining[p.index] >= amount
        ]
        if not candidates:
            _mark_unmatched(refund)
            continue
        # Exact amount first, then the most recent purchase before the refund.
        candidates.sort(key=lambda p: (p.spend != amount, -p.row.date.toordinal()))
        original = candidates[0]
        remaining[original.index] -= amount
        refund.refund_of = original.index
        refund.decision = Decision(
            original.decision.category_id,
            min(original.decision.confidence, 0.9),
            [
                f"Refund of {original.row.description!r} on {original.row.date.isoformat()}, "
                f"so it reduces {CATEGORIES[original.decision.category_id].name}"
            ],
            flags=[Flag.REFUND],
            suggestions=list(original.decision.suggestions),
        )


def _mark_unmatched(refund: _Draft) -> None:
    decision = refund.decision
    decision.flags.append(Flag.UNMATCHED_REFUND)
    if decision.category_id == NEEDS_REVIEW:
        decision.reasons.append("No matching purchase found in this file")
        return
    decision.confidence = min(decision.confidence, 0.8)
    decision.reasons.append(
        "No matching purchase in this file (it may be from an earlier statement); "
        "the merchant's usual category was used"
    )


# -- duplicates ------------------------------------------------------------------------------


def _flag_duplicates(drafts: list[_Draft], warnings: list[str]) -> None:
    groups: dict[tuple[date, str, Decimal, str], list[_Draft]] = defaultdict(list)
    for d in drafts:
        groups[(d.row.date, d.norm.key, d.spend, d.currency)].append(d)
    count = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        for d in group[1:]:
            d.extra_flags.append(Flag.POSSIBLE_DUPLICATE)
            d.extra_reasons.append(
                f"Same date, merchant and amount appears {len(group)} times; "
                "check it was not charged or listed twice"
            )
            count += 1
    if count:
        warnings.append(
            f"{count} transaction(s) look like duplicates of another line; they are flagged."
        )


# -- final status ----------------------------------------------------------------------------


def _finalize(
    d: _Draft, convention: Convention, statement_currency: str, settings: Settings
) -> Transaction:
    decision = d.decision
    reasons = list(decision.reasons) + d.extra_reasons
    flags = list(dict.fromkeys([*decision.flags, *d.extra_flags]))
    suggestions = list(decision.suggestions)
    category_id = decision.category_id
    confidence = decision.confidence
    force_review = False

    if d.currency != statement_currency:
        flags.append(Flag.FOREIGN_CURRENCY)
        reasons.append(
            f"Amount is in {d.currency} but the statement is in {statement_currency}; "
            "it was not converted, so please check it"
        )
        force_review = True

    category = CATEGORIES[category_id]
    decides_alone = category.kind is not Kind.NON_SPENDING and category_id != NEEDS_REVIEW
    if not force_review and decides_alone and confidence < settings.review_threshold:
        reasons.append(
            f"Confidence {confidence:.2f} is below the {settings.review_threshold:.2f} "
            "needed to decide automatically"
        )
        force_review = True

    if force_review and category_id != NEEDS_REVIEW:
        suggestions = list(dict.fromkeys([category_id, *suggestions]))
        category_id = NEEDS_REVIEW
        confidence = min(confidence, 0.5)
        category = CATEGORIES[NEEDS_REVIEW]

    if category_id == NEEDS_REVIEW:
        status = Status.NEEDS_REVIEW
    elif category.kind is Kind.NON_SPENDING:
        status = Status.EXCLUDED
    else:
        status = Status.CATEGORIZED

    if (
        category.kind is Kind.EXPENSE
        and d.spend >= settings.large_amount
        and Flag.LARGE_AMOUNT not in flags
    ):
        flags.append(Flag.LARGE_AMOUNT)
        reasons.append(f"Large amount ({d.spend:,.2f}), worth a second look")

    amount = d.row.amount
    if amount is None:
        amount = d.spend if convention is Convention.POSITIVE_IS_SPENDING else -d.spend

    return Transaction(
        id=d.txn_id,
        line=d.row.line,
        date=d.row.date,
        description=d.row.description,
        merchant=d.norm.key,
        amount=amount,
        spend_amount=d.spend,
        currency=d.currency,
        category_id=category_id,
        category_name=category.name,
        kind=category.kind,
        status=status,
        confidence=round(confidence, 2),
        reasons=tuple(reasons),
        flags=tuple(flags),
        refund_of=make_id(d.refund_of) if d.refund_of is not None else None,
        suggestions=tuple(s for s in suggestions if s in CATEGORIES and s != NEEDS_REVIEW),
    )
