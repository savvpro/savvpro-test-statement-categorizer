"""Loading and matching rules. The decisions themselves are in engine.py."""

import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

import yaml

from ..parsing.values import normalize_description

RULES_FILE = Path(__file__).with_name("rules.yaml")
MATCH_TYPES = ("exact", "starts_with", "contains")
BUSINESS_USE = ("always", "usually", "sometimes", "never")
KINDS = ("income", "expense", "tax", "transfer", "personal")


class RuleFileError(ValueError):
    pass


@lru_cache(maxsize=512)
def _word_pattern(text: str) -> re.Pattern:
    return re.compile(rf"(?<![A-Z0-9]){re.escape(text)}(?![A-Z0-9])")


def contains_words(haystack: str, needle: str) -> bool:
    return bool(_word_pattern(needle).search(haystack))


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: str
    match: str = "contains"
    category: str | None = None
    review: str | None = None  # rules that always send a row to review carry the reason
    suggest: str | None = None
    business_use: str = "always"
    source: str = "built-in"

    def matches(self, description: str) -> bool:
        if self.match == "exact":
            return description == self.pattern
        if self.match == "starts_with":
            return description == self.pattern or description.startswith(self.pattern + " ")
        return contains_words(description, self.pattern)

    @property
    def outcome(self) -> tuple:
        return (self.category, self.review is not None)


@dataclass(frozen=True)
class Stage:
    name: str
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class RuleBook:
    categories: dict[str, str]  # name -> kind
    stages: tuple[Stage, ...]
    refund_words: tuple[str, ...] = field(default_factory=tuple)

    def kind(self, category: str | None) -> str | None:
        return self.categories.get(category) if category else None

    def with_user_rules(self, user_rules: list[Rule]) -> "RuleBook":
        """User rules are checked first: they are decisions the user made on purpose."""
        if not user_rules:
            return self
        return replace(self, stages=(Stage("your rules", tuple(user_rules)),) + self.stages)

    def all_rules(self):
        for stage in self.stages:
            for rule in stage.rules:
                yield stage.name, rule

    def is_refund(self, description: str) -> bool:
        return any(contains_words(description, word) for word in self.refund_words)


@lru_cache(maxsize=4)
def load_rulebook(path: Path = RULES_FILE) -> RuleBook:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    categories = {}
    for item in data["categories"]:
        if item["kind"] not in KINDS:
            raise RuleFileError(f"category {item['name']}: unknown kind {item['kind']}")
        categories[item["name"]] = item["kind"]

    seen_ids = set()
    stages = []
    for stage in data["stages"]:
        rules = []
        for raw in stage["rules"]:
            rule = Rule(
                id=raw["id"],
                pattern=normalize_description(raw["pattern"]),
                match=raw.get("match", "contains"),
                category=raw.get("category"),
                review=raw.get("review"),
                suggest=raw.get("suggest"),
                business_use=raw.get("business_use", "always"),
            )
            _validate(rule, categories, seen_ids)
            seen_ids.add(rule.id)
            rules.append(rule)
        stages.append(Stage(stage["name"], tuple(rules)))

    refund_words = tuple(normalize_description(w) for w in data.get("refund_words", []))
    return RuleBook(categories, tuple(stages), refund_words)


def _validate(rule: Rule, categories: dict[str, str], seen_ids: set[str]) -> None:
    problem = None
    if rule.id in seen_ids:
        problem = "duplicate id"
    elif not rule.pattern:
        problem = "empty pattern"
    elif rule.match not in MATCH_TYPES:
        problem = f"unknown match type {rule.match}"
    elif rule.business_use not in BUSINESS_USE:
        problem = f"unknown business_use {rule.business_use}"
    elif bool(rule.category) == bool(rule.review):
        problem = "needs exactly one of category or review"
    elif rule.category and rule.category not in categories:
        problem = f"unknown category {rule.category}"
    elif rule.suggest and rule.suggest not in categories:
        problem = f"unknown suggested category {rule.suggest}"
    if problem:
        raise RuleFileError(f"rule {rule.id}: {problem}")


def user_rule(row: dict) -> Rule:
    """Build a Rule from a user_rules table row."""
    return Rule(
        id=f"USER-{row['id']}",
        pattern=row["pattern"],
        match=row["match_type"],
        category=row["category"],
        business_use="always",
        source="user",
    )
