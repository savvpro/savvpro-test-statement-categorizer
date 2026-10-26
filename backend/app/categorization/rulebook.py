"""Loads the merchant/keyword knowledge base from data, keeping rules out of code."""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from ..domain.models import Category

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "rules.json"


def contains_phrase(text: str, phrase: str) -> bool:
    """Whole-word match, so 'BP' does not fire inside 'BPX'."""
    return re.search(rf"(?<![A-Z0-9]){re.escape(phrase)}(?![A-Z0-9])", text) is not None


def contains_any(text: str, phrases: Tuple[str, ...]) -> bool:
    return any(contains_phrase(text, p) for p in phrases)


@dataclass(frozen=True)
class RuleMatch:
    category: Category
    weight: float
    pattern: str


@dataclass(frozen=True)
class RuleBook:
    weighted: Tuple[Tuple[str, Category, float], ...]
    mixed_use: Tuple[str, ...]
    transfer: Tuple[str, ...]
    refund: Tuple[str, ...]
    income: Tuple[str, ...]
    non_income_credit: Tuple[str, ...]

    @classmethod
    def load(cls, path: Path = DEFAULT_RULES_PATH) -> "RuleBook":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        weighted = tuple(
            (pattern, Category(category), float(weight))
            for category, patterns in data["categories"].items()
            for pattern, weight in patterns.items()
        )
        return cls(
            weighted=weighted,
            mixed_use=tuple(data["mixed_use"]),
            transfer=tuple(data["transfer"]),
            refund=tuple(data["refund"]),
            income=tuple(data["income"]),
            non_income_credit=tuple(data["non_income_credit"]),
        )

    def best_matches(self, text: str) -> List[RuleMatch]:
        """Strongest match per category, best first."""
        best: Dict[Category, RuleMatch] = {}
        for pattern, category, weight in self.weighted:
            current = best.get(category)
            if (current is None or weight > current.weight) and contains_phrase(text, pattern):
                best[category] = RuleMatch(category, weight, pattern)
        return sorted(best.values(), key=lambda m: -m.weight)
