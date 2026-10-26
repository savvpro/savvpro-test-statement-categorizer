"""The brain: plain, deterministic Python rules. No AI model is used.

Every row gets a category, a confidence, a reason and a needs_review flag.
When the code is not sure, it says so instead of guessing.
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal

from . import rules

# Things that are noise in a merchant name: store numbers, POS prefixes, etc.
_NOISE = re.compile(
    r"#\s*\d+"                                   # "#1234"
    r"|\b(?:POS|PURCHASE|CHECKCARD|TST|SQ)\b"    # processor prefixes
    r"|\*"                                       # "UBER *TRIP"
    r"|\b\d{3,}\b"                               # long numbers (ids)
)


def merchant_key(description: str) -> str:
    """Normalize a description so the same merchant gets the same key.

    'JOES CAFE 9921' -> 'JOES CAFE', 'UBER *TRIP 8841' -> 'UBER TRIP'
    """
    text = _NOISE.sub(" ", description.upper())
    text = re.sub(r"[^A-Z0-9&\- ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or description.upper().strip()


def merchant_word(key: str) -> str:
    """First word of the merchant key. Used to match refunds to charges."""
    return key.split(" ")[0] if key else ""


def _contains(text: str, words: list[str]) -> list[str]:
    """Return the keywords found in text, matching WHOLE words only.

    'RESTAURANT' matches 'THE RESTAURANT 22' but not 'RESTAURANTS DEPOT'.
    """
    found = []
    for w in words:
        if re.search(rf"(?<![A-Z0-9]){re.escape(w)}(?![A-Z0-9])", text):
            found.append(w)
    return found


@dataclass
class Result:
    category: str
    confidence: float
    reason: str
    needs_review: bool
    candidates: list = field(default_factory=list)


def _review(reason: str, candidates=()) -> Result:
    return Result(rules.NEEDS_REVIEW, 0.0, reason, True, list(candidates))


def _matching_categories(text: str) -> list[str]:
    return [cat for cat, words in rules.CATEGORIES.items() if _contains(text, words)]


def _money_in(text, word, seen_charges) -> Result:
    if _contains(text, rules.INCOME_WORDS):
        return Result("Income", 0.9, "Matches an income keyword", False)
    if _contains(text, rules.NOT_SPENDING):
        return Result(rules.NOT_SPENDING_LABEL, 0.95,
                      "Transfer or card payment, not income", False)

    if _contains(text, rules.REFUND_WORDS):
        # `word in seen_charges` (not just truthiness) so we can tell apart
        # "never seen this merchant" from "seen it under conflicting categories"
        # (stored as None).
        if word in seen_charges:
            earlier = seen_charges[word]
            if earlier is None:
                # Same merchant word was charged under different categories,
                # so we can't tell which one this refund belongs to.
                return _review("Merchant was charged under different categories; "
                               "cannot tell which one this refund is for",
                               [f"Refund: {c}" for c in _matching_categories(text)])
            return Result(f"Refund: {earlier}", 0.9,
                          f"Refund matches an earlier charge from {word}", False)

        matches = _matching_categories(text)
        if len(matches) == 1:
            return Result(f"Refund: {matches[0]}", 0.8,
                          "Refund keyword and merchant match, but the original "
                          "charge is not in this statement", False)
        return _review("Looks like a refund, but the original charge was not found",
                       matches)

    earlier = seen_charges.get(word)
    if earlier:
        return _review("Money in from a merchant you paid earlier; "
                       "could be a refund or something else",
                       [f"Refund: {earlier}", "Income"])
    return _review("Money in, source unclear (a refund is not income)", ["Income"])


def _money_out(text) -> Result:
    if _contains(text, rules.NOT_SPENDING):
        return Result(rules.NOT_SPENDING_LABEL, 0.95,
                      "Transfer or card payment, not spending", False)
    if _contains(text, rules.AMBIGUOUS):
        return _review("Merchant sells many kinds of things",
                       ["Office Supplies", "Software & Subscriptions", "Personal"])
    matches = _matching_categories(text)
    if len(matches) == 1:
        return Result(matches[0], 0.85, "Keyword match", False)
    if len(matches) > 1:
        return _review("Matches several categories", matches)
    return _review("Unknown merchant")


def categorize(description: str, amount: Decimal,
               user_rules: dict | None = None,
               seen_charges: dict | None = None) -> Result:
    """Categorize ONE transaction.

    user_rules:   merchant_key -> category the user chose earlier.
    seen_charges: merchant_word -> category of earlier charges (for refunds).
                  A value of None means the word was charged under
                  conflicting categories and must not be trusted.
    """
    user_rules = user_rules or {}
    seen_charges = seen_charges or {}
    text = description.upper()
    key = merchant_key(description)
    word = merchant_word(key)

    if key in user_rules:
        return Result(user_rules[key], 1.0, "You categorized this merchant before", False)
    if amount == 0:
        return _review("Zero amount")

    result = _money_in(text, word, seen_charges) if amount > 0 else _money_out(text)

    # Safety net: never let a low-confidence guess through.
    if not result.needs_review and result.confidence < rules.CONFIDENCE_THRESHOLD:
        return _review(f"Low confidence ({result.confidence:.2f})", [result.category])
    return result


def categorize_all(txns, user_rules: dict | None = None) -> list[dict]:
    """Categorize a whole statement. Returns rows in original file order."""
    seen: dict[str, str | None] = {}   # merchant_word -> category (None = conflict)
    seen_signatures = set()
    rows = []

    # Process charges before credits on the same day so refunds can find them.
    for t in sorted(txns, key=lambda x: (x.date, x.amount > 0, x.row)):
        key = merchant_key(t.description)
        word = merchant_word(key)
        res = categorize(t.description, t.amount, user_rules, seen)

        # Remember confident spending so a later refund can offset it.
                # Remember spending so a later refund can offset it.
        if t.amount < 0 and word and res.category != rules.NOT_SPENDING_LABEL:
            if res.needs_review:
                # We could not place this charge, so a refund from the same
                # merchant word cannot be matched with confidence.
                seen[word] = None
            elif word in seen and seen[word] != res.category:
                seen[word] = None      # same word, different categories: don't trust
            else:
                seen[word] = res.category

        signature = (t.date, t.description, str(t.amount))
        rows.append({
            "row": t.row,
            "date": t.date,
            "description": t.description,
            "amount": str(t.amount),
            "merchant_key": key,
            "category": res.category,
            "confidence": res.confidence,
            "reason": res.reason,
            "needs_review": res.needs_review,
            "candidates": res.candidates,
            "possible_duplicate": signature in seen_signatures,
        })
        seen_signatures.add(signature)

    return sorted(rows, key=lambda r: r["row"])


def summarize(rows: list[dict]) -> dict:
    """Totals per category. Refunds reduce the category they came from."""
    expenses: dict[str, Decimal] = {}
    income = Decimal(0)
    review_count = 0
    review_total = Decimal(0)
    excluded_count = 0

    for r in rows:
        amount = Decimal(r["amount"])
        category = r["category"]
        if r["needs_review"]:
            review_count += 1
            review_total += amount
        elif category == rules.NOT_SPENDING_LABEL:
            excluded_count += 1
        elif category == "Income":
            income += amount
        else:
            base = category.removeprefix("Refund: ")
            expenses[base] = expenses.get(base, Decimal(0)) - amount

    deductible = sum((v for k, v in expenses.items() if k != "Personal"), Decimal(0))
    return {
        "expenses": {k: str(v) for k, v in sorted(expenses.items())},
        "income": str(income),
        "deductible_total": str(deductible),
        "needs_review_count": review_count,
        "needs_review_total": str(review_total),
        "excluded_count": excluded_count,
    }