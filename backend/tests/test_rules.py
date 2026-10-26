import json
from decimal import Decimal

import pytest

from app.brain.categorizer import Categorizer
from app.brain.rules import DEFAULT_RULES_PATH, RulesError, load_rules
from app.categories import Category


def write_rules(tmp_path, **overrides):
    data = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf-8"))
    data.update(overrides)
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_shipped_rules_load():
    rules = load_rules()
    assert rules.structural and rules.income and rules.expense
    assert 0 < rules.review_threshold <= 1


def test_unknown_category_stops_startup(tmp_path):
    path = write_rules(tmp_path, expense=[{"pattern": "FOO", "category": "Fule"}])
    with pytest.raises(RulesError):
        load_rules(path)


def test_invalid_regex_stops_startup(tmp_path):
    path = write_rules(tmp_path, expense=[{"pattern": "(unclosed", "category": "Fuel"}])
    with pytest.raises(RulesError):
        load_rules(path)


def test_a_rule_cannot_assign_needs_review(tmp_path):
    path = write_rules(tmp_path, expense=[{"pattern": "FOO", "category": "Needs Review"}])
    with pytest.raises(RulesError):
        load_rules(path)


def test_missing_and_malformed_files(tmp_path):
    with pytest.raises(RulesError):
        load_rules(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(RulesError):
        load_rules(bad)


def test_rules_are_data_not_code(tmp_path):
    """Adding a merchant is a JSON edit; no Python changes."""
    path = write_rules(
        tmp_path,
        expense=[{"pattern": "HIGHWAY DINER", "category": "Personal", "confidence": 0.9}],
    )
    brain = Categorizer(load_rules(path))
    assert brain.categorize("HIGHWAY DINER 22", Decimal(-300)).category is Category.PERSONAL
    assert brain.categorize("SHELL", Decimal(-300)).category is Category.NEEDS_REVIEW


def test_patterns_match_whole_words_only(tmp_path):
    path = write_rules(tmp_path, expense=[{"pattern": "PSO", "category": "Fuel"}])
    brain = Categorizer(load_rules(path))
    assert brain.categorize("PSO 55", Decimal(-1)).category is Category.FUEL
    assert brain.categorize("PSOLUTIONS", Decimal(-1)).category is Category.NEEDS_REVIEW
