import shutil
from pathlib import Path

import pytest

from app.brain.rules import DATA_DIR, RulesError, load_rules, parse_rules
from app.brain.taxonomy import is_valid_category


def test_rules_load_and_reference_real_categories() -> None:
    rules = load_rules()

    assert len(rules.merchants) >= 60
    assert all(is_valid_category(c) for c in rules.merchants.values())
    assert all(is_valid_category(r.category) for r in rules.structural + rules.patterns)
    assert {a.id for a in rules.ambiguous} >= {"amazon", "p2p", "atm", "check", "chargeback"}


@pytest.fixture
def data_copy(tmp_path: Path) -> Path:
    for path in DATA_DIR.glob("*.yaml"):
        shutil.copy(path, tmp_path / path.name)
    return tmp_path


def test_unknown_category_in_merchants_raises(data_copy: Path) -> None:
    path = data_copy / "merchants.yaml"
    path.write_text(path.read_text() + "  FAKE VENDOR: snacks\n")

    with pytest.raises(RulesError, match="unknown category 'snacks'"):
        parse_rules(data_copy)


def test_unknown_category_in_patterns_raises(data_copy: Path) -> None:
    path = data_copy / "patterns.yaml"
    path.write_text(path.read_text().replace("category: travel", "category: vacation", 1))

    with pytest.raises(RulesError, match="vacation"):
        parse_rules(data_copy)


def test_bad_regex_raises(data_copy: Path) -> None:
    path = data_copy / "patterns.yaml"
    path.write_text(path.read_text().replace(r"'\bUBER ?\*? ?TRIP\b'", "'(UBER'", 1))

    with pytest.raises(RulesError, match="bad regex"):
        parse_rules(data_copy)


def test_unknown_suggestion_in_ambiguous_raises(data_copy: Path) -> None:
    path = data_copy / "ambiguous.yaml"
    path.write_text(path.read_text().replace("suggest: owner_draw", "suggest: cash", 1))

    with pytest.raises(RulesError, match="'cash'"):
        parse_rules(data_copy)
