"""Load and validate rules.yaml. Rules live outside the code so they can grow freely."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.engine.categories import CATEGORIES, NEEDS_REVIEW

DEFAULT_RULES_PATH = Path(__file__).with_name("rules.yaml")
LEVELS = ("merchant", "keyword", "weak")


@dataclass(frozen=True)
class Pattern:
    phrase: str
    category: str
    level: str  # "merchant" | "keyword" | "weak"
    regex: re.Pattern[str]


@dataclass(frozen=True)
class SpecialRule:
    name: str
    category: str
    sign: str  # "positive" | "negative" | "any"
    patterns: tuple[tuple[str, re.Pattern[str]], ...]


@dataclass(frozen=True)
class RuleSet:
    threshold: float
    confidence: dict[str, float]
    special_rules: tuple[SpecialRule, ...]
    patterns: tuple[Pattern, ...] = field(default_factory=tuple)


class RulesError(ValueError):
    pass


def phrase_regex(phrase: str) -> re.Pattern[str]:
    """Match a phrase only as whole words: 'ADS' matches 'META ADS', not 'ADSORB'."""
    return re.compile(rf"(?<![A-Z0-9]){re.escape(phrase.upper())}(?![A-Z0-9])")


def _check_category(name: str) -> str:
    if name not in CATEGORIES or name == NEEDS_REVIEW:
        raise RulesError(f"Unknown category in rules: {name!r}")
    return name


def build_rules(data: dict) -> RuleSet:
    confidence = {key: float(value) for key, value in data["confidence"].items()}
    for key in ("learned", "special", *LEVELS):
        if key not in confidence:
            raise RulesError(f"Missing confidence level: {key}")

    specials = []
    for rule in data.get("special_rules", []):
        sign = rule.get("sign", "any")
        if sign not in ("positive", "negative", "any"):
            raise RulesError(f"Bad sign {sign!r} in special rule {rule['name']}")
        specials.append(
            SpecialRule(
                name=rule["name"],
                category=_check_category(rule["category"]),
                sign=sign,
                patterns=tuple((str(k).upper(), phrase_regex(str(k))) for k in rule["keywords"]),
            )
        )

    patterns = []
    yaml_keys = {"merchant": "merchants", "keyword": "keywords", "weak": "weak_keywords"}
    for category, spec in (data.get("categories") or {}).items():
        _check_category(category)
        for level in LEVELS:
            for phrase in (spec or {}).get(yaml_keys[level], []) or []:
                phrase = str(phrase).upper()
                patterns.append(Pattern(phrase, category, level, phrase_regex(phrase)))

    return RuleSet(
        threshold=float(data.get("threshold", 0.7)),
        confidence=confidence,
        special_rules=tuple(specials),
        patterns=tuple(patterns),
    )


def load_rules(path: Path | str = DEFAULT_RULES_PATH) -> RuleSet:
    with open(path, encoding="utf-8") as handle:
        return build_rules(yaml.safe_load(handle))


@lru_cache(maxsize=1)
def default_rules() -> RuleSet:
    return load_rules(DEFAULT_RULES_PATH)
