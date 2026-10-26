"""The brain: decides the category of one transaction using plain rules.

Order of decisions (first one that applies wins):
  1. Transfers between own accounts -> "Not Spending"
  2. Refund wording                 -> "Refund" (if money came in)
  3. Keyword match, longest first   -> a spending category
  4. Anything unclear               -> "Needs Review" (with a reason)
"""
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from . import rules


@dataclass
class Result:
    category: str
    status: str  # "ok" or "needs_review"
    reason: str
    refund_of: Optional[str] = None


def normalize(description: str) -> str:
    """'Uber *Trip 8821' -> 'UBER TRIP'. Removes noise so rules match."""
    text = description.upper()
    text = re.sub(r"[*#_/,]", " ", text)
    text = re.sub(r"\b\d{3,}\b", " ", text)  # reference numbers
    return re.sub(r"\s+", " ", text).strip()


def _contains(text: str, phrase: str) -> bool:
    pattern = r"(?<![A-Z0-9])" + re.escape(phrase) + r"(?![A-Z0-9])"
    return re.search(pattern, text) is not None


def _best_match(text: str):
    """Return (category_or_None, matched_keywords). Longest keyword wins.

    category None means the best match was an ambiguous merchant or a tie
    between two different categories.
    """
    found = []
    for category, words in rules.KEYWORDS.items():
        for word in words:
            if _contains(text, word):
                found.append((len(word), word, category))
    for word in rules.AMBIGUOUS:
        if _contains(text, word):
            found.append((len(word), word, None))
    if not found:
        return "none", []
    longest = max(length for length, _, _ in found)
    top = [f for f in found if f[0] == longest]
    categories = {c for _, _, c in top}
    words = [w for _, w, _ in top]
    if len(categories) == 1:
        return categories.pop(), words
    return None, words  # tie between different categories


def categorize(description: str, amount: Decimal) -> Result:
    """amount: negative = money out (a charge), positive = money in."""
    text = normalize(description)
    if not text:
        return Result(rules.NEEDS_REVIEW, "needs_review", "Description is empty.")

    # 1. Transfers
    for phrase in rules.TRANSFER_PHRASES:
        if _contains(text, phrase):
            return Result(rules.NOT_SPENDING, "ok", f"Matched transfer phrase '{phrase}'.")

    has_refund_word = any(_contains(text, w) for w in rules.REFUND_WORDS)
    money_in = amount > 0
    category, words = _best_match(text)

    # 2. Money coming back
    if money_in:
        if has_refund_word or isinstance(category, str) and category != "none":
            original = category if category in rules.SPENDING_CATEGORIES else None
            note = f" from {words[0].title()}" if original else ""
            return Result(
                rules.REFUND, "ok",
                f"Money came back{note}. A refund is not income.",
                refund_of=original,
            )
        return Result(
            rules.NEEDS_REVIEW, "needs_review",
            "Money came in but this is not clearly a refund. It could be income.",
        )
    if has_refund_word:
        return Result(
            rules.NEEDS_REVIEW, "needs_review",
            "Says refund but money went out. Please check.",
        )

    # 3. Keyword match for charges
    if category == "none":
        return Result(rules.NEEDS_REVIEW, "needs_review", "No rule matches this merchant.")
    if category is None:
        return Result(
            rules.NEEDS_REVIEW, "needs_review",
            f"Could be more than one category ({', '.join(words)}).",
        )
    return Result(category, "ok", f"Matched keyword '{words[0]}'.")
