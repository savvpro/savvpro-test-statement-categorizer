import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from app.core.config import DEFAULT_KEYWORD_CONFIDENCE, DEFAULT_RULE_CONFIDENCE
from app.core.domain import AccountType, Category, Direction, Kind

RULES_PATH = Path(__file__).with_name("rules.yaml")
_WHITESPACE = re.compile(r"\s+")


class RulesError(ValueError):
    """rules.yaml is missing, unreadable or invalid. The message says where."""


def _clean(pattern: str) -> str:
    return _WHITESPACE.sub(" ", pattern.upper()).strip()


class Match(BaseModel):
    """Exactly one of the three. All are matched against the normalized text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    starts_with: str | None = None
    contains: str | None = None  # whole words only: "CAFE" does not match "CAFETERIA"
    regex: str | None = None  # case-insensitive search

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        given = [n for n in ("starts_with", "contains", "regex") if getattr(self, n) is not None]
        if len(given) != 1:
            raise ValueError(
                "match needs exactly one of starts_with, contains, regex "
                f"(got {', '.join(given) if given else 'none'})"
            )
        value = getattr(self, given[0])
        if not value.strip():
            raise ValueError(f"match.{given[0]} must not be empty")
        if given[0] == "regex":
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"invalid regex {value!r}: {exc}") from exc
        return self

    def matches(self, text: str) -> bool:
        if self.starts_with is not None:
            return text.startswith(_clean(self.starts_with))
        if self.contains is not None:
            phrase = re.escape(_clean(self.contains))
            return re.search(rf"(?<![A-Z0-9]){phrase}(?![A-Z0-9])", text) is not None
        return re.search(self.regex or "", text, re.IGNORECASE) is not None


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    match: Match
    category: Category
    kind: Kind | None = None  # omitted: money out -> expense, money in -> income
    confidence: float | None = Field(default=None, ge=0, le=1)  # omitted: section default
    account_type: AccountType | None = None
    direction: Direction | None = None
    reason: str

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must not be empty")
        return value.strip()

    def applies_to(self, text: str, account_type: AccountType, direction: Direction) -> bool:
        if self.account_type is not None and self.account_type != account_type:
            return False
        if self.direction is not None and self.direction != direction:
            return False
        return self.match.matches(text)


class RuleSet(BaseModel):
    """Sections in evaluation order: structural, merchants, review, keywords."""

    model_config = ConfigDict(extra="forbid")

    structural: list[Rule] = []
    merchants: list[Rule] = []
    review: list[Rule] = []
    keywords: list[Rule] = []

    @model_validator(mode="after")
    def _check_ids_and_fill_confidence(self) -> Self:
        seen: set[str] = set()
        for section, default in (
            ("structural", DEFAULT_RULE_CONFIDENCE),
            ("merchants", DEFAULT_RULE_CONFIDENCE),
            ("review", DEFAULT_RULE_CONFIDENCE),
            ("keywords", DEFAULT_KEYWORD_CONFIDENCE),
        ):
            for rule in getattr(self, section):
                if rule.id in seen:
                    raise ValueError(f"duplicate rule id {rule.id!r}")
                seen.add(rule.id)
                if rule.confidence is None:
                    rule.confidence = default
        return self


def _describe(exc: ValidationError, data: Any) -> list[str]:
    lines = []
    for err in exc.errors():
        loc = err["loc"]
        path = "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in loc).lstrip(".")
        rule_id = ""
        if len(loc) >= 2 and isinstance(loc[1], int) and isinstance(data, dict):
            section = data.get(loc[0])
            if isinstance(section, list) and loc[1] < len(section):
                item = section[loc[1]]
                if isinstance(item, dict) and "id" in item:
                    rule_id = f" (rule {item['id']!r})"
        lines.append(f"  {path or 'rules'}{rule_id}: {err['msg']}")
    return lines


def load_rules(path: Path | str = RULES_PATH) -> RuleSet:
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RulesError(f"Cannot read rules file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise RulesError(f"Rules file {path} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise RulesError(f"Rules file {path} must contain sections (structural, merchants, ...)")
    try:
        return RuleSet.model_validate(data)
    except ValidationError as exc:
        raise RulesError(
            f"Invalid rules in {path}:\n" + "\n".join(_describe(exc, data))
        ) from exc


@lru_cache(maxsize=1)
def default_rules() -> RuleSet:
    return load_rules(RULES_PATH)
