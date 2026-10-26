"""The brain: decide a category for each transaction, or admit it is not sure.

Order of checks for one row:
  1. Learned rules  - the user already told us what this exact merchant is (1.00).
  2. Special rules  - refunds, card payments, transfers, bank fees (0.95), sign-checked.
  3. Category rules - known merchant (0.90) > keyword (0.75) > weak keyword (0.50).
  4. Decision       - one winning category with confidence >= threshold, otherwise
                      Needs Review with a reason explaining why.

Every result says *why* (reason) and *where the answer came from* (source).
No LLMs, no network: plain, testable Python.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date

from app.engine.categories import INCOME, NEEDS_REVIEW, category_kind
from app.engine.duplicates import find_duplicates
from app.engine.normalizer import Normalized, normalize
from app.engine.rules import LEVELS, RuleSet, default_rules

LEVEL_LABEL = {"merchant": "Merchant", "keyword": "Keyword", "weak": "Weak keyword"}


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float
    reason: str
    source: str  # "rule" | "learned" | "user" | "none"
    normalized_merchant: str
    needs_review: bool = False
    is_duplicate: bool = False
    suggested_category: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StatementRow:
    """Minimal input the brain needs: no parser or database types leak in here."""

    date: date
    description: str
    amount: float
    currency: str = "USD"
    row_number: int | None = None


def _review(
    merchant: str,
    reason: str,
    *,
    confidence: float = 0.0,
    source: str = "none",
    suggested: str | None = None,
    notes: tuple[str, ...] = (),
) -> Classification:
    return Classification(
        category=NEEDS_REVIEW,
        confidence=round(confidence, 2),
        reason=reason,
        source=source,
        normalized_merchant=merchant,
        needs_review=True,
        suggested_category=suggested,
        notes=notes,
    )


def _sign_ok(sign: str, amount: float) -> bool:
    if sign == "positive":
        return amount > 0
    if sign == "negative":
        return amount < 0
    return True


def _currency_notes(norm: Normalized, currency: str) -> tuple[str, ...]:
    if norm.foreign_currency and norm.foreign_amount is not None:
        if norm.foreign_currency != currency:
            return (
                f"Foreign currency: original charge {norm.foreign_amount:,.2f} "
                f"{norm.foreign_currency}",
            )
        return (f"Description mentions {norm.foreign_amount:,.2f} {norm.foreign_currency}",)
    return ()


def classify(
    description: str,
    amount: float,
    *,
    currency: str = "USD",
    learned: Mapping[str, str] | None = None,
    rules: RuleSet | None = None,
) -> Classification:
    rules = rules or default_rules()
    norm = normalize(description)
    merchant = norm.merchant
    notes = _currency_notes(norm, currency)
    conf = rules.confidence

    # 1. Learned rules: the user's own decision for this exact merchant wins.
    if learned and merchant in learned:
        category = learned[merchant]
        return Classification(
            category=category,
            confidence=conf["learned"],
            reason=f"You categorized '{merchant}' as {category} before",
            source="learned",
            normalized_merchant=merchant,
            notes=notes,
        )

    # 2. Special rules (refund / card payment / transfer / bank fees), sign-aware.
    wrong_sign = None
    for rule in rules.special_rules:
        hit = next((phrase for phrase, rx in rule.patterns if rx.search(merchant)), None)
        if hit is None:
            continue
        if _sign_ok(rule.sign, amount):
            return Classification(
                category=rule.category,
                confidence=conf["special"],
                reason=f"'{hit}' matched {rule.category}",
                source="rule",
                normalized_merchant=merchant,
                notes=notes,
            )
        wrong_sign = wrong_sign or (rule, hit)
    if wrong_sign:
        rule, hit = wrong_sign
        direction = "came in" if amount > 0 else "went out"
        return _review(
            merchant,
            f"'{hit}' suggests {rule.category}, but money {direction}",
            confidence=conf["weak"],
            suggested=rule.category,
            notes=notes,
        )

    # 3. Category rules: take the strongest level that matched anything.
    matches = [p for p in rules.patterns if p.regex.search(merchant)]
    # A longer, more specific merchant beats a shorter one it contains:
    # "UBER EATS" (Meals) wins over "UBER" (Travel).
    matches = [
        p
        for p in matches
        if not any(o is not p and p.phrase in o.phrase and o.phrase != p.phrase for o in matches)
    ]
    for level in LEVELS:
        hits = [p for p in matches if p.level == level]
        if not hits:
            continue
        categories = sorted({p.category for p in hits})
        level_conf = conf[level]
        if len(categories) > 1:
            detail = ", ".join(f"{p.category} ({p.phrase})" for p in hits)
            return _review(
                merchant,
                f"Multiple matches: {detail}",
                confidence=level_conf / len(categories),
                notes=notes,
            )
        category, phrase = categories[0], hits[0].phrase
        label = LEVEL_LABEL[level]

        # 4. Decision, with sanity checks on the direction of money.
        if level_conf < rules.threshold:
            return _review(
                merchant,
                f"Only a weak hint: '{phrase}' suggests {category} "
                f"({level_conf:.0%} < {rules.threshold:.0%})",
                confidence=level_conf,
                source="rule",
                suggested=category,
                notes=notes,
            )
        kind = category_kind(category)
        if kind == "spending" and amount > 0:
            return _review(
                merchant,
                f"Money came in from '{phrase}' ({category}) without refund wording; "
                "could be a refund or a credit",
                confidence=conf["weak"],
                source="rule",
                suggested=category,
                notes=notes,
            )
        if category == INCOME and amount < 0:
            return _review(
                merchant,
                f"'{phrase}' looks like income, but money went out",
                confidence=conf["weak"],
                source="rule",
                suggested=category,
                notes=notes,
            )
        return Classification(
            category=category,
            confidence=level_conf,
            reason=f"{label} '{phrase}' matched {category}",
            source="rule",
            normalized_merchant=merchant,
            notes=notes,
        )

    if amount > 0:
        return _review(
            merchant,
            f"Money came in from unknown '{merchant}'; not guessing income or refund",
            notes=notes,
        )
    return _review(merchant, f"No rule matched '{merchant}'", notes=notes)


def classify_statement(
    rows: Sequence[StatementRow],
    *,
    learned: Mapping[str, str] | None = None,
    rules: RuleSet | None = None,
) -> list[Classification]:
    """Classify every row, then flag possible duplicates (later copy -> Needs Review)."""
    results = [
        classify(row.description, row.amount, currency=row.currency, learned=learned, rules=rules)
        for row in rows
    ]
    keys = [
        (row.date, row.amount, result.normalized_merchant)
        for row, result in zip(rows, results, strict=True)
    ]
    for index, original in find_duplicates(keys).items():
        result = results[index]
        first = rows[original].row_number or original + 1
        was = result.suggested_category or result.category
        results[index] = replace(
            result,
            category=NEEDS_REVIEW,
            needs_review=True,
            is_duplicate=True,
            suggested_category=None if was == NEEDS_REVIEW else was,
            reason=f"Possible duplicate of row {first} (same date, amount and merchant); "
            f"was: {result.reason}",
        )
    return results
