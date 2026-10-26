"""The brain: deterministic, rule-based categorizer. No ML / LLM involved."""
import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from . import rules as R

REVIEW_THRESHOLD = 0.7
FUZZY_CUTOFF = 85

_MERCHANT_RES = [(k, R.keyword_re(k), c) for k, c in sorted(R.MERCHANTS.items(), key=lambda kv: -len(kv[0]))]
_AMBIGUOUS_RES = [(k, R.keyword_re(k)) for k in R.AMBIGUOUS]
_FUZZY_KEYS = [k for k in R.MERCHANTS if re.fullmatch(r"[A-Z]{5,}", k)]


@dataclass
class Result:
    norm: str
    kind: str  # spend | refund | income | transfer
    category: str
    confidence: float
    reason: str

    @property
    def needs_review(self) -> bool:
        return self.category == R.REVIEW or self.confidence < REVIEW_THRESHOLD


def normalize(desc: str) -> str:
    """'UBER *TRIP 8F3K2' -> 'UBER TRIP'. Drops store numbers, ref codes, '*' noise."""
    s = re.sub(r"[^A-Z0-9&'.\-#/ ]", " ", desc.upper().replace("*", " "))
    tokens = []
    for t in s.split():
        if t.startswith("#") or t.isdigit():
            continue
        if len(t) >= 4 and any(c.isdigit() for c in t) and any(c.isalpha() for c in t):
            continue
        tokens.append(t.strip("."))
    return " ".join(t for t in tokens if t) or desc.upper().strip()


def kind_for(category: str, amount: float) -> str:
    if category == R.INCOME:
        return "income"
    if category == R.NOT_SPENDING:
        return "transfer"
    return "spend" if amount < 0 else "refund"


class Brain:
    def __init__(self) -> None:
        self.user_rules: dict[str, str] = {}  # normalized description -> category

    def learn(self, norm: str, category: str) -> None:
        self.user_rules[norm] = category

    def classify(self, description: str, amount: float) -> Result:
        """amount: negative = money out, positive = money in."""
        norm = normalize(description)

        if norm in self.user_rules:  # 1. rules the user taught us always win
            cat = self.user_rules[norm]
            return Result(norm, kind_for(cat, amount), cat, 1.0, "Matches a rule you saved")

        if R.PAYMENT_RE.search(norm) or R.TRANSFER_RE.search(norm):  # 2. not spending
            return Result(norm, "transfer", R.NOT_SPENDING, 0.95, "Transfer or card payment, not spending")

        if amount < 0 and R.FEE_RE.search(norm):  # 3. fees / interest
            return Result(norm, "spend", "Bank Fees & Interest", 0.95, "Fee or interest charge")

        cat, conf, reason = self._match_merchant(norm)  # 4. merchants

        if amount > 0:  # money in: never assume it is income
            if cat != R.REVIEW and conf >= 0.7:
                return Result(norm, "refund", cat, conf * 0.9,
                              "Credit from a known merchant: treated as a refund, not income")
            if R.INCOME_RE.search(norm):
                return Result(norm, "income", R.INCOME, 0.85, "Looks like client payment / deposit")
            why = "Refund from an unrecognized merchant" if R.REFUND_RE.search(norm) else "Unrecognized credit"
            return Result(norm, "refund", R.REVIEW, 0.0, why)

        return Result(norm, "spend", cat, conf, reason)

    def _match_merchant(self, norm: str) -> tuple[str, float, str]:
        for key, rx, cat in _MERCHANT_RES:
            if rx.search(norm):
                return cat, 0.95, f"Matched merchant '{key}'"
        for key, rx in _AMBIGUOUS_RES:
            if rx.search(norm):
                return R.REVIEW, 0.3, f"'{key}' could be many things, please review"
        for token in (t for t in norm.split() if len(t) >= 5):  # typos
            hit = process.extractOne(token, _FUZZY_KEYS, scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
            if hit:
                return R.MERCHANTS[hit[0]], 0.75, f"Fuzzy match: '{token}' is close to '{hit[0]}'"
        return R.REVIEW, 0.0, "Unknown merchant"
