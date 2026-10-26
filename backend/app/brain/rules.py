"""Loads and validates rules.json.

The rules are data so a non-developer can add a merchant without touching code.
Validation runs at startup: a typo in a category name stops the server instead of
silently mis-categorising someone's tax return.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

from ..categories import Category

DEFAULT_RULES_PATH = Path(__file__).parent / "rules.json"


class RulesError(ValueError):
    pass


class RuleSpec(BaseModel):
    pattern: str
    category: Category
    confidence: float = Field(default=0.9, gt=0.0, le=1.0)

    @field_validator("pattern")
    @classmethod
    def _compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"invalid regular expression {value!r}: {exc}") from exc
        return value


class FuzzySpec(BaseModel):
    min_score: int = Field(default=80, ge=1, le=100)
    scale: float = Field(default=0.85, gt=0.0, le=1.0)


class RulesFile(BaseModel):
    version: int = 1
    review_threshold: float = Field(default=0.75, gt=0.0, le=1.0)
    learned_confidence: float = Field(default=0.97, gt=0.0, le=1.0)
    fuzzy: FuzzySpec = FuzzySpec()
    noise_words: list[str] = []
    structural: list[RuleSpec] = []
    income: list[RuleSpec] = []
    refund_words: str
    expense: list[RuleSpec] = []
    always_review: list[str] = []


@dataclass(frozen=True)
class Rule:
    regex: re.Pattern[str]
    category: Category
    confidence: float


@dataclass(frozen=True)
class Rules:
    structural: tuple[Rule, ...]
    income: tuple[Rule, ...]
    expense: tuple[Rule, ...]
    refund_words: re.Pattern[str]
    always_review: re.Pattern[str]
    noise_words: re.Pattern[str] | None
    review_threshold: float
    learned_confidence: float
    fuzzy_min_score: int
    fuzzy_scale: float


def _words(pattern: str) -> re.Pattern[str]:
    """Whole-word match, so PSO does not fire inside 'PSOLUTIONS' or TOLL inside 'STOLLEN'."""
    return re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE)


def _compile(specs: list[RuleSpec]) -> tuple[Rule, ...]:
    return tuple(Rule(_words(s.pattern), s.category, s.confidence) for s in specs)


def load_rules(path: Path | None = None) -> Rules:
    path = path or DEFAULT_RULES_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        spec = RulesFile.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise RulesError(f"Cannot load rules from {path}: {exc}") from exc

    for section in (spec.structural, spec.income, spec.expense):
        for rule in section:
            if rule.category is Category.NEEDS_REVIEW:
                raise RulesError("A rule cannot assign 'Needs Review'; leave the row unmatched.")

    escape = re.escape
    return Rules(
        structural=_compile(spec.structural),
        income=_compile(spec.income),
        expense=_compile(spec.expense),
        refund_words=_words(spec.refund_words),
        always_review=_words("|".join(escape(w) for w in spec.always_review) or r"(?!)"),
        noise_words=_words("|".join(escape(w) for w in spec.noise_words))
        if spec.noise_words
        else None,
        review_threshold=spec.review_threshold,
        learned_confidence=spec.learned_confidence,
        fuzzy_min_score=spec.fuzzy.min_score,
        fuzzy_scale=spec.fuzzy.scale,
    )
