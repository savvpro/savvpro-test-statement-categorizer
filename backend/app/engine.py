"""Pure, conservative decision engine; no database, network, ML, or demo-specific logic."""

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .domain import CATEGORIES, ENGINE_VERSION, EXPENSE_CATEGORIES


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    phrases: tuple[str, ...]
    strength: int = 95
    requires_context: bool = False


@dataclass
class Decision:
    kind: str = "unknown"
    category: str = "uncategorized"
    status: str = "needs_review"
    strength: int = 0
    rule_ids: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    explanation: str = "No supported evidence. Please choose the transaction purpose."
    reason: str | None = "unknown_merchant"
    engine_version: str = ENGINE_VERSION

    def to_dict(self):
        return asdict(self)


def normalize(description: str) -> str:
    value = unicodedata.normalize("NFKC", description).casefold()
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def contains(text: str, phrase: str) -> bool:
    return f" {normalize(phrase)} " in f" {text} "


def load_rules() -> tuple[Rule, ...]:
    data = json.loads(Path(__file__).with_name("rules.json").read_text())
    seen = set()
    result = []
    for item in data:
        rule = Rule(**{**item, "phrases": tuple(item["phrases"])})
        if rule.id in seen or rule.category not in EXPENSE_CATEGORIES or not rule.phrases:
            raise ValueError(f"Invalid categorization rule: {rule.id}")
        if rule.strength not in (70, 95) or any(not normalize(p) for p in rule.phrases):
            raise ValueError(f"Invalid evidence strength or phrase: {rule.id}")
        seen.add(rule.id)
        result.append(rule)
    return tuple(result)


DEFAULT_RULES = load_rules()
REFUND_MARKERS = ("refund", "refunded", "reversal", "purchase return")
TRANSFER_MARKERS = (
    "transfer to savings",
    "transfer from savings",
    "transfer to checking",
    "transfer from checking",
    "internal transfer",
    "credit card payment",
    "card repayment",
    "transfer between accounts",
)
INCOME_MARKERS = ("client invoice payment", "consulting invoice payment", "salary payment")


def classify(description: str, amount_minor: int, rules: tuple[Rule, ...] = DEFAULT_RULES):
    text = normalize(description)
    hits = sorted(
        [(r, p) for r in rules for p in r.phrases if contains(text, p)],
        key=lambda hit: (hit[0].id, hit[1]),
    )
    refunds = [p for p in REFUND_MARKERS if contains(text, p)]
    transfers = [p for p in TRANSFER_MARKERS if contains(text, p)]
    income = [p for p in INCOME_MARKERS if contains(text, p)]
    evidence = [f"Matched “{p}”" for _, p in hits]
    evidence += [f"Transaction marker “{p}”" for p in refunds + transfers + income]
    decision = Decision(rule_ids=sorted({r.id for r, _ in hits}), evidence=evidence)
    if amount_minor == 0:
        decision.reason = "zero_amount"
        decision.explanation = "Zero-value entry. Confirm what this row represents."
        return decision
    if (
        sum(bool(x) for x in (refunds, transfers, income)) > 1
        or (refunds or income)
        and amount_minor < 0
        or transfers
        and hits
    ):
        decision.reason = "semantic_conflict"
        decision.explanation = "Description and transaction evidence disagree. Review is required."
        return decision
    if transfers:
        return Decision(
            "transfer",
            "transfers",
            "categorized",
            95,
            ["kind.transfer"],
            evidence,
            "Explicit account-movement marker; excluded from business spending.",
            None,
        )
    if income:
        return Decision(
            "income",
            "income",
            "categorized",
            95,
            ["kind.income"],
            evidence,
            "Explicit income marker on an incoming transaction.",
            None,
        )
    if amount_minor > 0 and not refunds:
        decision.reason = "unexplained_credit"
        decision.explanation = "Incoming money is not automatically income. Confirm its purpose."
        return decision
    decision.kind = "refund" if refunds else "expense"
    categories = {r.category for r, _ in hits}
    if len(categories) > 1:
        decision.reason = "conflicting_rules"
        decision.explanation = "Rules suggest different categories. No category was selected."
        return decision
    if not hits:
        decision.explanation = (
            "Refund marker found, but the original expense category is unknown."
            if refunds
            else "Merchant or business purpose is unknown. Please review this outgoing transaction."
        )
        decision.reason = "refund_category_unknown" if refunds else "unknown_merchant"
        return decision
    decision.category = next(iter(categories))
    decision.strength = max(r.strength for r, _ in hits)
    if any(r.requires_context for r, _ in hits) or decision.strength < 90:
        decision.reason = "business_context_required"
        decision.explanation = (
            f"{CATEGORIES[decision.category]} is a suggestion. Business purpose needs confirmation."
        )
        return decision
    decision.status = "categorized"
    decision.reason = None
    decision.explanation = (
        f"Explicit refund with {CATEGORIES[decision.category]} evidence; offsets expenses."
        if refunds
        else f"Specific merchant evidence supports {CATEGORIES[decision.category]}."
    )
    return decision
