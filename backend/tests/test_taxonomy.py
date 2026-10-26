from pathlib import Path

import pytest

from app.brain.models import CategoryKind
from app.brain.taxonomy import (
    NEEDS_REVIEW,
    TaxonomyError,
    all_categories,
    get_category,
    is_valid_category,
    parse_taxonomy,
)

VALID_ENTRY = """
  - id: {id}
    label: {label}
    kind: {kind}
    schedule_c_line: null
    deductible_pct: {pct}
    description: Test category.
"""


def write_yaml(tmp_path: Path, *entries: str) -> Path:
    path = tmp_path / "categories.yaml"
    path.write_text("categories:\n" + "".join(entries), encoding="utf-8")
    return path


def entry(id: str, kind: str = "expense", pct: int = 100) -> str:
    return VALID_ENTRY.format(id=id, label=id.title(), kind=kind, pct=pct)


REVIEW = entry(NEEDS_REVIEW, kind="review", pct=0)


def test_default_taxonomy_loads() -> None:
    categories = all_categories()

    assert len(categories) == 26
    assert len({c.id for c in categories}) == len(categories)


def test_meals_is_half_deductible() -> None:
    meals = get_category("meals")

    assert meals.kind is CategoryKind.expense
    assert meals.deductible_pct == 50


def test_needs_review_exists() -> None:
    assert is_valid_category(NEEDS_REVIEW)
    assert get_category(NEEDS_REVIEW).kind is CategoryKind.review


def test_non_expenses_are_not_deductible() -> None:
    for category in all_categories():
        if category.kind is not CategoryKind.expense:
            assert category.deductible_pct == 0, category.id


def test_unknown_category() -> None:
    assert not is_valid_category("groceries")
    with pytest.raises(KeyError):
        get_category("groceries")


def test_valid_custom_file(tmp_path: Path) -> None:
    taxonomy = parse_taxonomy(write_yaml(tmp_path, entry("software"), REVIEW))

    assert [c.id for c in taxonomy.all()] == ["software", NEEDS_REVIEW]


def test_duplicate_ids_raise(tmp_path: Path) -> None:
    path = write_yaml(tmp_path, entry("software"), entry("software"), REVIEW)

    with pytest.raises(TaxonomyError, match="duplicate"):
        parse_taxonomy(path)


def test_missing_needs_review_raises(tmp_path: Path) -> None:
    with pytest.raises(TaxonomyError, match=NEEDS_REVIEW):
        parse_taxonomy(write_yaml(tmp_path, entry("software")))


def test_invalid_kind_raises(tmp_path: Path) -> None:
    with pytest.raises(TaxonomyError, match="invalid category"):
        parse_taxonomy(write_yaml(tmp_path, entry("software", kind="spending"), REVIEW))


@pytest.mark.parametrize("pct", [-1, 101])
def test_pct_out_of_range_raises(tmp_path: Path, pct: int) -> None:
    with pytest.raises(TaxonomyError, match="invalid category"):
        parse_taxonomy(write_yaml(tmp_path, entry("software", pct=pct), REVIEW))


def test_deductible_non_expense_raises(tmp_path: Path) -> None:
    with pytest.raises(TaxonomyError, match="not an expense"):
        parse_taxonomy(write_yaml(tmp_path, entry("salary", kind="income", pct=100), REVIEW))


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "categories.yaml"
    path.write_text("categories: [unclosed\n", encoding="utf-8")

    with pytest.raises(TaxonomyError, match="cannot read"):
        parse_taxonomy(path)


def test_wrong_shape_raises(tmp_path: Path) -> None:
    path = tmp_path / "categories.yaml"
    path.write_text("- just a list\n", encoding="utf-8")

    with pytest.raises(TaxonomyError, match="top-level"):
        parse_taxonomy(path)
