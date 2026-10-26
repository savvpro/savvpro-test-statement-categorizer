"""The brain: deterministic, explainable categorization. No ML, no LLM.

Decision order for each transaction:
  1. The user's own correction for this merchant (always wins).
  2. The best matching rule (highest confidence, then longest keyword).
  3. Sanity checks that can demote an answer to "Needs Review"
     (duplicates, unusually large amounts).
  4. Anything below CONFIDENCE_THRESHOLD, or with no match, is "Needs Review"
     with the reason and the best suggestion.
Direction matters: money in with an expense category is a *refund* (it reduces
that category), never income.
"""

import re
from collections import Counter
from decimal import Decimal
from functools import lru_cache

from . import rules as r
from .models import CategorizedTransaction, CategoryTotal, Kind, RawTransaction, Summary
from .normalize import clean, merchant_key


@lru_cache(maxsize=None)
def _pattern(keyword: str) -> re.Pattern:
    return re.compile(rf"(?:^| ){re.escape(clean(keyword))}(?: |$)")


def match_rule(text: str, amount: Decimal) -> tuple[r.Rule, str] | None:
    direction = "in" if amount > 0 else "out"
    best: tuple[r.Rule, str] | None = None
    for rule in r.RULES:
        if rule.direction not in (None, direction):
            continue
        for keyword in rule.keywords:
            if _pattern(keyword).search(text):
                if best is None or (rule.confidence, len(keyword)) > (best[0].confidence, len(best[1])):
                    best = (rule, keyword)
    return best


def kind_for(category: str, amount: Decimal) -> Kind:
    if category == r.INCOME:
        return "income"
    if category == r.TRANSFER:
        return "transfer"
    return "refund" if amount > 0 else ("personal" if category == r.PERSONAL else "expense")


def _decide(txn: RawTransaction, key: str, overrides: dict[str, str]) -> tuple[str, float, str]:
    """Returns (category, confidence, reason) before sanity checks."""
    if key in overrides:
        return overrides[key], 1.0, "Set by you"

    text = clean(txn.description)
    found = match_rule(text, txn.amount)
    if found:
        rule, keyword = found
        reason = f"Matched '{keyword}'" + (f". {rule.note}" if rule.note else "")
        return rule.category, rule.confidence, reason

    if txn.amount > 0:
        hint = "Refund of an unrecognised purchase" if "REFUND" in text or "REVERSAL" in text else "Unrecognised deposit"
        return r.INCOME, 0.0, f"{hint}: could be income, a refund, a loan or a gift"
    return r.REVIEW, 0.0, "Merchant not recognised"


def categorize(
    transactions: list[RawTransaction], overrides: dict[str, str] | None = None
) -> list[CategorizedTransaction]:
    overrides = {merchant_key(k): v for k, v in (overrides or {}).items() if v in r.ALL_CATEGORIES}
    seen: Counter = Counter()
    results = []

    for index, txn in enumerate(transactions):
        key = merchant_key(txn.description)
        category, confidence, reason = _decide(txn, key, overrides)
        user_set = key in overrides

        if not user_set:
            fingerprint = (txn.date, txn.amount, clean(txn.description))
            seen[fingerprint] += 1
            if seen[fingerprint] > 1:
                confidence = min(confidence, 0.5)
                reason += ". Possible duplicate: same date, amount and description appeared earlier"
            if txn.amount < -r.LARGE_EXPENSE and category not in (r.TRANSFER, r.INCOME):
                confidence = min(confidence, 0.6)
                reason += f". Unusually large (over {r.LARGE_EXPENSE})"
            if category == r.MEALS and txn.amount < -r.LARGE_MEAL:
                confidence = min(confidence, 0.6)
                reason += f". Large meal (over {r.LARGE_MEAL}): check the business purpose"

        needs_review = confidence < r.CONFIDENCE_THRESHOLD
        suggestion = category if category != r.REVIEW else None
        if needs_review:
            final, kind = r.REVIEW, "review"
            reason = f"Not sure ({round(confidence * 100)}%): {reason}"
        else:
            final, kind = category, kind_for(category, txn.amount)
            if kind == "refund":
                reason += f". Money back: reduces {category}, not counted as income"

        results.append(
            CategorizedTransaction(
                id=index,
                date=txn.date,
                description=txn.description,
                amount=txn.amount,
                merchant_key=key,
                category=final,
                suggested_category=suggestion if needs_review else None,
                kind=kind,
                confidence=round(confidence, 2),
                reason=reason,
                needs_review=needs_review,
            )
        )
    return results


def summarize(transactions: list[CategorizedTransaction]) -> Summary:
    zero = Decimal(0)
    per_category: dict[str, list] = {c: [0, zero] for c in r.EXPENSE_CATEGORIES}
    personal = income = transfers = review_amount = zero
    review_count = 0

    for t in transactions:
        if t.kind in ("expense", "refund") and t.category in per_category:
            per_category[t.category][0] += 1
            per_category[t.category][1] += -t.amount  # spending positive, refunds reduce it
        elif t.kind == "personal" or (t.kind == "refund" and t.category == r.PERSONAL):
            personal += -t.amount
        elif t.kind == "income":
            income += t.amount
        elif t.kind == "transfer":
            transfers += abs(t.amount)
        elif t.kind == "review":
            review_count += 1
            review_amount += t.amount

    categories = [CategoryTotal(category=c, count=n, total=total) for c, (n, total) in per_category.items() if n]
    return Summary(
        expense_categories=categories,
        business_expenses=sum((c.total for c in categories), zero),
        personal_spending=personal,
        income=income,
        transfers_excluded=transfers,
        needs_review_count=review_count,
        needs_review_amount=review_amount,
    )
