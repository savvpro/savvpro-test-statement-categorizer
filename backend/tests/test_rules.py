from pathlib import Path

import pytest

from app.brain.rules import Match, RulesError, RuleSet, default_rules, load_rules


def rule(**overrides):
    base = {
        "id": "r1",
        "match": {"contains": "X"},
        "category": "Meals",
        "reason": "because",
    }
    return {**base, **overrides}


def write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "rules.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_shipped_rules_load() -> None:
    rules = default_rules()
    assert rules.structural and rules.merchants and rules.review and rules.keywords


def test_default_confidences_by_section() -> None:
    rules = RuleSet.model_validate(
        {
            "structural": [rule(id="a")],
            "merchants": [rule(id="b")],
            "review": [rule(id="c")],
            "keywords": [rule(id="d"), rule(id="e", confidence=0.9)],
        }
    )
    assert [r.confidence for r in rules.structural + rules.merchants + rules.review] == [0.95] * 3
    assert [r.confidence for r in rules.keywords] == [0.75, 0.9]


@pytest.mark.parametrize(
    ("match", "text", "expected"),
    [
        ({"contains": "CAFE"}, "BLUE BIRD CAFE F-7", True),
        ({"contains": "CAFE"}, "CAFETERIA", False),
        ({"contains": "CAFE"}, "MYCAFE", False),
        ({"contains": "CAFE"}, "JOES-CAFE", True),
        ({"contains": "AMAZON"}, "AWS EMEA AWS.AMAZON.CO LU", True),
        ({"contains": "cafe"}, "BLUE BIRD CAFE", True),  # pattern is uppercased
        ({"contains": "BIRD   CAFE"}, "BLUE BIRD CAFE", True),  # and spaces collapsed
        ({"contains": "ZONG"}, "ZONG 4G DEVICE RECHARGE", True),
        ({"contains": "4G"}, "ZONG 4G DEVICE", True),
        ({"contains": "UBER *TRIP"}, "UBER *TRIP HELP.UBER.COM", True),
        ({"starts_with": "AWS"}, "AWS EMEA", True),
        ({"starts_with": "AWS"}, "FOREIGN TXN FEE AWS EMEA", False),
        ({"starts_with": "aws"}, "AWS EMEA", True),
        ({"regex": r"^IBFT TO .+ACCOUNTANTS$"}, "IBFT TO KASHIF & CO CHARTERED ACCOUNTANTS", True),
        ({"regex": r"^IBFT TO .+ACCOUNTANTS$"}, "IBFT TO ALI RAZA ****4410", False),
        ({"regex": r"cafe|bakery"}, "BLUE BIRD CAFE", True),  # regex ignores case
    ],
)
def test_match(match: dict, text: str, expected: bool) -> None:
    assert Match(**match).matches(text) is expected


@pytest.mark.parametrize(
    ("bad_rule", "message"),
    [
        (rule(match={}), "exactly one of"),
        (rule(match={"contains": "A", "starts_with": "B"}), "exactly one of"),
        (rule(match={"contains": "  "}), "must not be empty"),
        (rule(match={"regex": "("}), "invalid regex"),
        (rule(match={"contans": "A"}), "contans"),
        (rule(category="Groceries"), "category"),
        (rule(kind="spending"), "kind"),
        (rule(confidence=1.5), "confidence"),
        (rule(confidence=-0.1), "confidence"),
        (rule(direction="sideways"), "direction"),
        (rule(account_type="wallet"), "account_type"),
        (rule(id="Has Spaces"), "id"),
        (rule(reason="  "), "reason must not be empty"),
        (rule(colour="red"), "colour"),
    ],
)
def test_invalid_rule_is_rejected_with_a_clear_error(
    tmp_path: Path, bad_rule: dict, message: str
) -> None:
    import yaml

    path = write(tmp_path, yaml.safe_dump({"merchants": [rule(id="good"), bad_rule]}))
    with pytest.raises(RulesError) as exc:
        load_rules(path)
    text = str(exc.value)
    assert message in text
    assert "merchants[1]" in text  # says which rule


def test_missing_required_field_names_the_rule(tmp_path: Path) -> None:
    content = "keywords:\n  - id: kw1\n    match: {contains: X}\n    category: Meals\n"
    path = write(tmp_path, content)
    with pytest.raises(RulesError, match=r"keywords\[0\]\.reason \(rule 'kw1'\): Field required"):
        load_rules(path)


def test_duplicate_ids_across_sections_rejected(tmp_path: Path) -> None:
    import yaml

    data = {"merchants": [rule(id="same")], "keywords": [rule(id="same")]}
    with pytest.raises(RulesError, match="duplicate rule id 'same'"):
        load_rules(write(tmp_path, yaml.safe_dump(data)))


def test_unknown_section_rejected(tmp_path: Path) -> None:
    with pytest.raises(RulesError, match="structurl"):
        load_rules(write(tmp_path, "structurl: []\n"))


@pytest.mark.parametrize("content", ["", "- just\n- a list\n", "merchants: [unclosed\n"])
def test_unusable_file_rejected(tmp_path: Path, content: str) -> None:
    with pytest.raises(RulesError):
        load_rules(write(tmp_path, content))


def test_missing_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(RulesError, match="Cannot read"):
        load_rules(tmp_path / "nope.yaml")
