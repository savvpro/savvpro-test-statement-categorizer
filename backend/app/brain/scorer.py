"""Candidate scoring – combines merchant dict, keyword rules, and modifiers.

Returns (category_slug, confidence, reasons[]).
"""
from __future__ import annotations

import contextlib
from typing import Any

from app.brain.keywords import KEYWORD_RULES
from app.brain.merchants import MERCHANT_DICT
from app.brain.taxonomy import TxKind


def score_candidates(
    merchant: str,
    kind: TxKind,
    amount_cents: int,
    *,
    user_rules: list[dict[str, Any]] | None = None,
    account_type: str = "checking",
    equipment_demin_cents: int = 250_000,
) -> tuple[list[tuple[str, float, list[str]]], bool, bool]:
    """Return scored category candidates, sorted descending by confidence.

    Returns (candidates, mixed_use, always_review); each candidate is
    (category_slug, confidence, reason_list).
    """
    candidates: dict[str, tuple[float, list[str]]] = {}
    mixed_use = False
    always_review = False

    def _add(slug: str, conf: float, reason: str) -> None:
        prev_conf, prev_reasons = candidates.get(slug, (0.0, []))
        if conf > prev_conf:
            candidates[slug] = (conf, prev_reasons + [reason])
        else:
            candidates[slug] = (prev_conf, prev_reasons + [reason])

    # ── 1. User rules (highest priority) ──────────────────────────────────────
    import re as _re
    if user_rules:
        for rule in sorted(user_rules, key=lambda r: r.get("priority", 0), reverse=True):
            if not rule.get("enabled", True):
                continue
            match_type = rule.get("match_type", "contains")
            pattern = rule.get("pattern", "")
            cat_slug = rule.get("category_slug", "")
            matched = False
            if match_type == "merchant_exact":
                matched = merchant == pattern.upper()
            elif match_type == "contains":
                matched = pattern.upper() in merchant
            elif match_type == "regex":
                with contextlib.suppress(_re.error):
                    matched = bool(_re.search(pattern, merchant, _re.I))
            if matched:
                _add(cat_slug, 0.99, f"User rule: '{pattern}' → {cat_slug}")
                break  # user rules are mutually exclusive

    # ── 2. Merchant dictionary ─────────────────────────────────────────────────
    # Try exact, then prefix matches
    entry = MERCHANT_DICT.get(merchant)
    if entry is None:
        # Try progressively shorter prefixes (min 2 chars handles "B&H")
        for n in range(len(merchant) - 1, 1, -1):
            candidate = merchant[:n].rstrip()
            entry = MERCHANT_DICT.get(candidate)
            if entry:
                break
    if entry:
        _add(entry.category_slug, entry.confidence,
             f"Merchant dictionary: '{merchant}' → {entry.category_slug} ({entry.confidence:.2f})")
        if entry.mixed_use:
            mixed_use = True
        # Check note
        if entry.note:
            pass  # notes used in review_reason construction upstream

    # ── 3. Keyword rules ───────────────────────────────────────────────────────
    for kw in KEYWORD_RULES:
        if kw.pattern in merchant:
            _add(kw.category_slug, kw.confidence,
                 f"Keyword '{kw.pattern}' → {kw.category_slug} ({kw.confidence:.2f})")

    # ── 4. Kind-based defaults (fall-through) ─────────────────────────────────
    if kind == TxKind.FEE and "bank_fees" not in candidates:
        _add("bank_fees", 0.85, "Kind=fee → bank_fees")
    elif kind == TxKind.INTEREST_INCOME and "interest_income" not in candidates:
        _add("interest_income", 0.90, "Kind=interest_income")
    elif kind == TxKind.INTEREST_EXPENSE and "interest_expense" not in candidates:
        _add("interest_expense", 0.90, "Kind=interest_expense")
    elif kind in {TxKind.TRANSFER, TxKind.CC_PAYMENT, TxKind.OWNER_DRAW,
                  TxKind.OWNER_CONTRIB, TxKind.TAX_PAYMENT, TxKind.LOAN_PAYMENT}:
        _add("non_pl", 0.95, f"Kind={kind} → non-P&L movement")
    elif kind == TxKind.INCOME and "client_income" not in candidates:
        _add("client_income", 0.80, "Kind=income → client_income (default)")
    elif kind == TxKind.REFUND and not candidates:
        # Refund without prior match – unknown category
        _add("non_pl", 0.70, "Kind=refund, no prior category match")

    # ── 5. Amount modifiers ────────────────────────────────────────────────────
    abs_amount = abs(amount_cents)

    # Equipment threshold: if > de-minimis, flag even if confident
    if "equipment" in candidates and abs_amount > equipment_demin_cents:
        slug, (conf, reasons) = "equipment", candidates["equipment"]
        candidates[slug] = (conf, reasons + [
            f"Amount ${abs_amount/100:.2f} > $2,500 de-minimis limit, always review"
        ])
        always_review = True

    # Large "meals" are suspicious (could be catering/event)
    if "meals" in candidates and abs_amount > 25_000:  # >$250
        conf, reasons = candidates["meals"]
        candidates["meals"] = (conf * 0.85, reasons + [
            "Large meal amount, possible catering or personal event, confidence reduced"
        ])

    # ── Collect and sort ───────────────────────────────────────────────────────
    result = [
        (slug, conf, reasons)
        for slug, (conf, reasons) in candidates.items()
    ]
    result.sort(key=lambda x: x[1], reverse=True)

    return result, mixed_use, always_review
