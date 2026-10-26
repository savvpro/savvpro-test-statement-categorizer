"""Merchant rule table: loading, validation and phrase matching."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.brain.categories import CATEGORIES

DATA_FILE = Path(__file__).parent / "data" / "merchants.json"


class RuleKind(StrEnum):
    BRAND = "brand"
    AMBIGUOUS = "ambiguous"
    KEYWORD = "keyword"


@dataclass(frozen=True)
class Rule:
    kind: RuleKind
    phrase: tuple[str, ...]  # tokens that must appear consecutively
    category: str | None  # None for ambiguous rules
    confidence: float
    candidates: tuple[str, ...] = ()
    note: str = ""

    @property
    def specificity(self) -> tuple[int, int]:
        """Longer phrases win: AMAZON WEB SERVICES beats AMAZON, UBER EATS beats UBER."""
        return (len(self.phrase), sum(len(t) for t in self.phrase))

    @property
    def text(self) -> str:
        return " ".join(self.phrase)


class RuleTable:
    def __init__(self, rules: list[Rule]):
        self._rules = rules

    def __len__(self) -> int:
        return len(self._rules)

    def match(self, tokens: tuple[str, ...]) -> list[Rule]:
        return [r for r in self._rules if _contains_phrase(tokens, r.phrase)]

    @classmethod
    def load(cls, path: Path = DATA_FILE) -> RuleTable:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(_build_rules(data))


def _contains_phrase(tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    n = len(phrase)
    return any(tokens[i : i + n] == phrase for i in range(len(tokens) - n + 1))


def _check_category(category_id: str, where: str) -> None:
    if category_id not in CATEGORIES:
        raise ValueError(f"{where}: unknown category {category_id!r}")


def _tokens(phrase: str) -> tuple[str, ...]:
    # Same treatment the normalizer gives descriptions: hyphens split words, apostrophes vanish.
    return tuple(phrase.replace("'", "").replace("-", " ").upper().split())


def _build_rules(data: dict[str, Any]) -> list[Rule]:
    rules: list[Rule] = []
    for group in data.get("brands", []):
        _check_category(group["category"], "brands")
        for phrase in group["match"]:
            rules.append(
                Rule(RuleKind.BRAND, _tokens(phrase), group["category"], group["confidence"])
            )
    for group in data.get("ambiguous", []):
        for candidate in group["candidates"]:
            _check_category(candidate, "ambiguous")
        for phrase in group["match"]:
            rules.append(
                Rule(
                    RuleKind.AMBIGUOUS,
                    _tokens(phrase),
                    None,
                    0.0,
                    tuple(group["candidates"]),
                    group.get("note", ""),
                )
            )
    for group in data.get("keywords", []):
        _check_category(group["category"], "keywords")
        for phrase in group["match"]:
            rules.append(
                Rule(RuleKind.KEYWORD, _tokens(phrase), group["category"], group["confidence"])
            )
    return rules
