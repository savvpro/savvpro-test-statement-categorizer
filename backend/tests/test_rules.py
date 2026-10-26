import pytest

from app.engine.categories import CATEGORIES, category_kind
from app.engine.rules import RulesError, build_rules, default_rules, phrase_regex

BASE_CONF = {"learned": 1, "special": 0.95, "merchant": 0.9, "keyword": 0.75, "weak": 0.5}


def test_default_rules_load_and_only_use_known_categories():
    rules = default_rules()
    assert rules.threshold == 0.70
    assert {p.category for p in rules.patterns} <= set(CATEGORIES)
    assert [r.name for r in rules.special_rules] == [
        "refund",
        "card_payment",
        "transfer",
        "bank_fees",
    ]


def test_unknown_category_is_rejected():
    with pytest.raises(RulesError, match="Unknown category"):
        build_rules({"confidence": BASE_CONF, "categories": {"Snacks": {"keywords": ["X"]}}})


def test_needs_review_cannot_be_a_rule_target():
    with pytest.raises(RulesError):
        build_rules({"confidence": BASE_CONF, "categories": {"Needs Review": {}}})


def test_missing_confidence_level_is_rejected():
    with pytest.raises(RulesError, match="Missing confidence"):
        build_rules({"confidence": {"learned": 1}})


def test_bad_sign_is_rejected():
    data = {
        "confidence": BASE_CONF,
        "special_rules": [{"name": "x", "category": "Refund", "sign": "up", "keywords": ["X"]}],
    }
    with pytest.raises(RulesError, match="Bad sign"):
        build_rules(data)


def test_phrase_regex_whole_words():
    assert phrase_regex("ADS").search("META ADS")
    assert not phrase_regex("ADS").search("ROADSIDE")
    assert phrase_regex("AT&T").search("AT&T WIRELESS")


@pytest.mark.parametrize(
    ("category", "kind"),
    [
        ("Meals", "spending"),
        ("Refund", "refund"),
        ("Income", "income"),
        ("Transfer (not spending)", "not_spending"),
        ("Card Payment (not spending)", "not_spending"),
        ("Needs Review", "review"),
    ],
)
def test_category_kind(category, kind):
    assert category_kind(category) == kind
