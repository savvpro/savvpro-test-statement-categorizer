"""Load and validate the YAML rule files. Rules are data; the engine is code.

Validation fails fast at startup: a bad rule file is a configuration bug, not a runtime surprise.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.domain.enums import AccountType, Category, Direction, Flag

MAX_SCORE = 0.99


class RuleFileError(ValueError):
    """Raised when a rule file is malformed."""


@dataclass(frozen=True, slots=True)
class PatternRule:
    """Regex rule used by the structural and keyword stages."""

    id: str
    pattern: re.Pattern[str]
    category: Category
    score: float
    directions: frozenset[Direction]
    account_types: frozenset[AccountType]
    flags: frozenset[Flag]
    is_refund: bool = False


@dataclass(frozen=True, slots=True)
class MerchantRule:
    id: str
    aliases: tuple[str, ...]
    alias_patterns: tuple[re.Pattern[str], ...]
    category: Category
    score: float
    flags: frozenset[Flag]


@dataclass(frozen=True, slots=True)
class RuleSet:
    structural: tuple[PatternRule, ...]
    merchants: tuple[MerchantRule, ...]
    keywords: tuple[PatternRule, ...]
    mixed_use: tuple[re.Pattern[str], ...]
    mixed_use_names: tuple[str, ...]


def token_pattern(alias: str) -> re.Pattern[str]:
    """Match `alias` as whole tokens anywhere in a merchant key."""
    return re.compile(r"(?:^|\s)" + re.escape(alias.upper()) + r"(?:\s|$)")


def _enum_set[E: (Direction, AccountType, Flag)](
    values: Iterable[str] | None, enum: type[E], default: Iterable[E], where: str
) -> frozenset[E]:
    if values is None:
        return frozenset(default)
    try:
        return frozenset(enum(v) for v in values)
    except ValueError as exc:
        raise RuleFileError(f"{where}: {exc}") from exc


def _category(value: Any, where: str) -> Category:
    try:
        return Category(value)
    except ValueError as exc:
        raise RuleFileError(f"{where}: unknown category {value!r}") from exc


def _score(value: Any, where: str) -> float:
    if not isinstance(value, int | float) or not 0 < float(value) <= MAX_SCORE:
        raise RuleFileError(f"{where}: score must be in (0, {MAX_SCORE}], got {value!r}")
    return float(value)


def _compile(pattern: Any, where: str) -> re.Pattern[str]:
    if not isinstance(pattern, str) or not pattern:
        raise RuleFileError(f"{where}: pattern must be a non-empty string")
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise RuleFileError(f"{where}: invalid regex: {exc}") from exc


def _pattern_rules(items: list[Mapping[str, Any]], file: str, score_key: str) -> list[PatternRule]:
    rules: list[PatternRule] = []
    for item in items:
        rid = str(item.get("id", ""))
        where = f"{file}:{rid or '?'}"
        rules.append(
            PatternRule(
                id=rid,
                pattern=_compile(item.get("pattern"), where),
                category=_category(item.get("category"), where),
                score=_score(item.get(score_key), where),
                directions=_enum_set(item.get("directions"), Direction, Direction, where),
                account_types=_enum_set(item.get("account_types"), AccountType, AccountType, where),
                flags=_enum_set(item.get("flags"), Flag, (), where),
                is_refund=bool(item.get("is_refund", False)),
            )
        )
    return rules


def _merchant_rules(items: list[Mapping[str, Any]]) -> list[MerchantRule]:
    rules: list[MerchantRule] = []
    for item in items:
        rid = str(item.get("id", ""))
        where = f"merchants.yaml:{rid or '?'}"
        aliases = item.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            raise RuleFileError(f"{where}: aliases must be a non-empty list")
        names = tuple(str(a).upper() for a in aliases)
        rules.append(
            MerchantRule(
                id=rid,
                aliases=names,
                alias_patterns=tuple(token_pattern(a) for a in names),
                category=_category(item.get("category"), where),
                score=_score(item.get("score"), where),
                flags=_enum_set(item.get("flags"), Flag, (), where),
            )
        )
    return rules


def _load_list(path: Path) -> list[Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, list):
        raise RuleFileError(f"{path.name}: top level must be a list")
    return data


def _check_unique_ids(ids: Iterable[str]) -> None:
    seen: set[str] = set()
    for rid in ids:
        if not rid:
            raise RuleFileError("every rule needs a non-empty id")
        if rid in seen:
            raise RuleFileError(f"duplicate rule id {rid!r}")
        seen.add(rid)


def _check_alias_collisions(merchants: Iterable[MerchantRule]) -> None:
    owner: dict[str, Category] = {}
    for rule in merchants:
        for alias in rule.aliases:
            if alias in owner and owner[alias] is not rule.category:
                raise RuleFileError(
                    f"alias {alias!r} maps to both {owner[alias]} and {rule.category}"
                )
            owner[alias] = rule.category


def load_ruleset(rules_dir: Path) -> RuleSet:
    structural = _pattern_rules(_load_list(rules_dir / "structural.yaml"), "structural", "score")
    keywords = _pattern_rules(_load_list(rules_dir / "keywords.yaml"), "keywords", "weight")
    merchants = _merchant_rules(_load_list(rules_dir / "merchants.yaml"))
    mixed = tuple(str(a).upper() for a in _load_list(rules_dir / "mixed_use.yaml"))

    _check_unique_ids(
        [r.id for r in structural] + [r.id for r in keywords] + [r.id for r in merchants]
    )
    _check_alias_collisions(merchants)

    return RuleSet(
        structural=tuple(structural),
        merchants=tuple(merchants),
        keywords=tuple(keywords),
        mixed_use=tuple(token_pattern(a) for a in mixed),
        mixed_use_names=mixed,
    )


DEFAULT_RULES_DIR = Path(__file__).resolve().parents[2] / "rules"
