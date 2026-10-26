"""The brain.

A deterministic, rule-based categorizer - no AI model decides anything here
(the task's one big rule). Pipeline per transaction:

    1. normalize the description
    2. special flows first: transfers -> income -> refunds (credits)
    3. otherwise keyword scoring across spending categories
    4. confidence scoring + ambiguity dampening
    5. below the "confirm" threshold => Needs Review (honest uncertainty)

Batch step: duplicate detection (same date + amount + merchant).
"""

from .. import config
from ..models import ParsedTransaction, Summary, TransactionOut
from . import rules as rules_mod
from .normalizer import normalize, strip_noise


def _score_keywords(text: str, entries: list[dict]) -> tuple[float, list[str]]:
    """Best keyword weight in `text` + which keywords matched."""
    best, matched = 0.0, []
    for entry in entries:
        if entry["kw"] in text:
            matched.append(entry["kw"])
            best = max(best, float(entry["w"]))
    return best, matched


def _best_spending_match(text: str) -> tuple[str | None, float, list[str], str | None, float]:
    """Score `text` against every spending category.

    Returns (best_category, best_score, matched_keywords, second_category, second_score).
    """
    best_cat, best_w, best_kw = None, 0.0, []
    second_cat, second_w = None, 0.0
    for cat in rules_mod.spending_categories():
        w, kw = _score_keywords(text, cat["keywords"])
        if w <= 0.0:
            continue
        if w > best_w:
            second_cat, second_w = best_cat, best_w
            best_cat, best_w, best_kw = cat["name"], w, kw
        elif w > second_w:
            second_cat, second_w = cat["name"], w
    return best_cat, best_w, best_kw, second_cat, second_w


def _out(category, confidence, txn, norm, *, band, reasons=None, flags=None,
         linked=None, is_spending=True) -> TransactionOut:
    return TransactionOut(
        id=0,  # assigned in batch step
        date=txn.date,
        description=txn.description,
        normalized=norm,
        amount=txn.amount,
        direction="in" if txn.amount > 0 else "out",
        category=category,
        linked_category=linked,
        confidence=round(confidence, 2),
        band=band,
        needs_review=band != "high",
        is_spending=is_spending,
        flags=flags or [],
        reasons=reasons or [],
    )


def _review(txn, norm, reason: str, flags=None) -> TransactionOut:
    return _out(None, 0.0, txn, norm, band="low", reasons=[reason], flags=flags,
                is_spending=False)


def categorize_one(txn: ParsedTransaction) -> TransactionOut:
    """Decide one transaction. Pure function - no state, no network, no AI."""
    norm = normalize(txn.description)

    if any("unreadable date" in i for i in txn.issues):
        return _review(txn, norm, "could not read the date on this row")

    if "missing amount" in txn.issues:
        return _review(txn, norm, "amount missing or unreadable on this row")

    if txn.amount == 0:
        return _review(txn, norm, "zero amount - nothing to categorize")

    # -- 1. Transfers first: moving your own money is never spending/income --
    t_w, t_kw = _score_keywords(norm, rules_mod.special_keywords("transfers"))
    if t_w >= 0.8:
        return _out(
            config.CATEGORY_TRANSFERS, min(0.95, 0.7 + t_w * 0.25), txn, norm,
            band="high", is_spending=False,
            reasons=[f"transfer pattern matched: {', '.join(t_kw)} - moving money "
                     f"between own accounts is not spending"],
        )

    # -- 2. Money in (credits): income vs refund - the classic tax-time trap --
    if txn.amount > 0:
        i_w, i_kw = _score_keywords(norm, rules_mod.special_keywords("income"))
        if i_w >= 0.8:
            return _out(
                config.CATEGORY_INCOME, min(0.95, 0.6 + i_w * 0.35), txn, norm,
                band="high", is_spending=False,
                reasons=[f"income pattern matched: {', '.join(i_kw)}"],
            )

        r_w, r_kw = _score_keywords(norm, rules_mod.special_keywords("refund"))
        cat, w, kw, _, _ = _best_spending_match(strip_noise(norm))
        if r_w >= 0.7:
            reasons = [f"refund pattern matched: {', '.join(r_kw)} - money back, not income"]
            if cat and w >= config.REFUND_LINK_CONFIDENCE:
                reasons.append(f"merchant '{kw[0]}' links it to {cat}")
                return _out(config.CATEGORY_REFUNDS, min(0.95, w), txn, norm, band="high",
                            reasons=reasons, linked=cat, is_spending=False)
            return _out(config.CATEGORY_REFUNDS, 0.8, txn, norm, band="high",
                        reasons=reasons, is_spending=False)

        # Credit with no explicit signal: a known expense merchant refunding us?
        if cat and w >= 0.75:
            return _out(
                config.CATEGORY_REFUNDS, round(w * 0.9, 2), txn, norm, band="high",
                reasons=[f"credit from a known expense merchant ({kw[0]}) - treated as a "
                         f"refund, not income"], linked=cat, is_spending=False,
            )
        return _review(txn, norm,
                       "money came in but it is unclear if this is client income or a refund")

    # -- 3. Money out: keyword scoring across spending categories --
    text = strip_noise(norm)
    cat, w, kw, second_cat, second_w = _best_spending_match(text)
    if not cat:
        return _review(txn, norm, "no rule matched this description")

    conf = w
    if len(kw) >= 2:
        conf = min(0.95, conf + 0.05)  # two independent hits reinforce each other

    reasons = [f"matched '{kw[0]}' -> {cat}"]
    if second_cat and second_w >= config.AMBIGUITY_RATIO * w and second_w >= 0.5:
        conf *= config.AMBIGUITY_PENALTY
        reasons.append(f"also resembles {second_cat} - confidence reduced, please confirm")

    if conf >= config.AUTO_CONFIDENCE:
        band = "high"
    elif conf >= config.CONFIRM_CONFIDENCE:
        band = "medium"
        reasons.append("medium confidence - please confirm")
    else:
        return _review(txn, norm,
                       f"closest guess was {cat} ({conf:.2f}) - too unsure to assign")

    return _out(cat, conf, txn, norm, band=band, reasons=reasons,
                is_spending=cat not in config.NON_SPENDING)


def categorize_statement(parsed: list[ParsedTransaction]) -> tuple[list[TransactionOut], Summary]:
    """Categorize all rows, then run batch-level checks (duplicates)."""
    results = [categorize_one(t) for t in parsed]
    for i, r in enumerate(results):
        r.id = i + 1

    seen: dict[tuple, int] = {}
    for r in results:
        key = (r.date, round(r.amount, 2), r.normalized)
        if key in seen:
            r.flags.append("possible_duplicate")
            r.reasons.append(
                f"same date, amount and merchant as row {seen[key]} - verify it is "
                f"not a double charge")
            r.needs_review = True
        else:
            seen[key] = r.id

    return results, _summarize(results)


def _summarize(results: list[TransactionOut]) -> Summary:
    s = Summary(count=len(results))
    for r in results:
        amount = abs(round(r.amount, 2))
        if r.category == config.CATEGORY_INCOME:
            s.income_total += amount
        elif r.category == config.CATEGORY_REFUNDS:
            s.refunds_total += amount
        elif r.category == config.CATEGORY_TRANSFERS:
            s.transfers_total += amount
        elif r.amount < 0 and r.category is not None:
            s.by_category[r.category] = round(s.by_category.get(r.category, 0.0) + amount, 2)
            s.spending_total = round(s.spending_total + amount, 2)
        if r.needs_review:
            s.review_count += 1
    return s
