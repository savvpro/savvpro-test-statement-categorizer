"""Load and validate the rule data files in brain/data/ once."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.brain.models import AccountType
from app.brain.taxonomy import Taxonomy, load_taxonomy

DATA_DIR = Path(__file__).parent / "data"
DIRECTIONS = {"in", "out"}


class RulesError(ValueError):
    """A rule file is malformed or points at an unknown category."""


@dataclass(frozen=True, slots=True)
class PatternRule:
    id: str
    regex: re.Pattern[str]
    category: str
    direction: str | None = None
    account: AccountType | None = None

    def applies(self, text: str, direction: str | None, account: AccountType) -> bool:
        if self.direction and direction and self.direction != direction:
            return False
        if self.account and self.account is not account:
            return False
        return bool(self.regex.search(text))


@dataclass(frozen=True, slots=True)
class AmbiguousRule:
    id: str
    regex: re.Pattern[str]
    reason: str
    suggest: str | None = None
    always: bool = False


@dataclass(frozen=True, slots=True)
class Rules:
    merchants: dict[str, str]
    structural: list[PatternRule]
    patterns: list[PatternRule]
    keywords: dict[str, str]  # KEYWORD -> category
    ambiguous: list[AmbiguousRule]


def _read(path: Path, key: str) -> object:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RulesError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(data, dict) or key not in data:
        raise RulesError(f"{path.name}: expected a top-level {key!r} key")
    return data[key]


def _category(taxonomy: Taxonomy, value: object, where: str) -> str:
    if not isinstance(value, str) or value not in taxonomy:
        raise RulesError(f"{where}: unknown category {value!r}")
    return value


def _regex(value: object, where: str) -> re.Pattern[str]:
    try:
        return re.compile(str(value))
    except re.error as exc:
        raise RulesError(f"{where}: bad regex: {exc}") from exc


def _pattern_rules(items: object, taxonomy: Taxonomy, where: str) -> list[PatternRule]:
    if not isinstance(items, list):
        raise RulesError(f"{where}: expected a list")
    rules = []
    for item in items:
        rule_where = f"{where}[{item.get('id', '?') if isinstance(item, dict) else '?'}]"
        if not isinstance(item, dict) or not item.get("id") or "regex" not in item:
            raise RulesError(f"{rule_where}: each rule needs id and regex")
        direction = item.get("direction")
        if direction is not None and direction not in DIRECTIONS:
            raise RulesError(f"{rule_where}: direction must be in/out")
        account = item.get("account")
        try:
            account_type = AccountType(account) if account else None
        except ValueError:
            raise RulesError(f"{rule_where}: unknown account {account!r}") from None
        rules.append(
            PatternRule(
                id=str(item["id"]),
                regex=_regex(item["regex"], rule_where),
                category=_category(taxonomy, item.get("category"), rule_where),
                direction=direction,
                account=account_type,
            )
        )
    return rules


def parse_rules(data_dir: Path = DATA_DIR, taxonomy: Taxonomy | None = None) -> Rules:
    taxonomy = taxonomy or load_taxonomy()

    merchants_raw = _read(data_dir / "merchants.yaml", "merchants")
    if not isinstance(merchants_raw, dict):
        raise RulesError("merchants.yaml: expected a mapping")
    merchants = {
        str(name).upper(): _category(taxonomy, category, f"merchants.yaml[{name}]")
        for name, category in merchants_raw.items()
    }

    structural = _pattern_rules(
        _read(data_dir / "patterns.yaml", "structural"), taxonomy, "patterns.structural"
    )
    patterns = _pattern_rules(
        _read(data_dir / "patterns.yaml", "patterns"), taxonomy, "patterns.patterns"
    )
    ids = [rule.id for rule in structural + patterns]
    if len(ids) != len(set(ids)):
        raise RulesError("patterns.yaml: duplicate rule ids")

    keywords_raw = _read(data_dir / "keywords.yaml", "keywords")
    if not isinstance(keywords_raw, dict):
        raise RulesError("keywords.yaml: expected a mapping")
    keywords = {
        str(word).upper(): _category(taxonomy, category, f"keywords.yaml[{category}]")
        for category, words in keywords_raw.items()
        for word in words
    }

    ambiguous = []
    for item in _read(data_dir / "ambiguous.yaml", "ambiguous") or []:
        where = f"ambiguous.yaml[{item.get('id', '?')}]"
        suggest = item.get("suggest")
        ambiguous.append(
            AmbiguousRule(
                id=str(item["id"]),
                regex=_regex(item["regex"], where),
                reason=str(item.get("reason", "ambiguous merchant")),
                suggest=_category(taxonomy, suggest, where) if suggest else None,
                always=bool(item.get("always", False)),
            )
        )

    return Rules(merchants, structural, patterns, keywords, ambiguous)


@lru_cache
def load_rules() -> Rules:
    return parse_rules()
