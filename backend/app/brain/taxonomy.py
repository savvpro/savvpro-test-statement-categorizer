"""Category taxonomy loaded from `data/categories.yaml` and validated once."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.brain.models import CategoryKind

DEFAULT_PATH = Path(__file__).parent / "data" / "categories.yaml"
NEEDS_REVIEW = "needs_review"


class TaxonomyError(ValueError):
    """Raised when the categories file is missing, malformed or inconsistent."""


class Category(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1)
    kind: CategoryKind
    schedule_c_line: str | None
    deductible_pct: int = Field(ge=0, le=100)
    description: str = Field(min_length=1)


class Taxonomy:
    def __init__(self, categories: list[Category]) -> None:
        self._by_id = {category.id: category for category in categories}

    def get(self, category_id: str) -> Category:
        try:
            return self._by_id[category_id]
        except KeyError:
            raise KeyError(f"unknown category: {category_id!r}") from None

    def all(self) -> list[Category]:
        return list(self._by_id.values())

    def __contains__(self, category_id: object) -> bool:
        return category_id in self._by_id


def parse_taxonomy(path: Path) -> Taxonomy:
    """Read and validate a categories file. Uncached; use `load_taxonomy` in app code."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TaxonomyError(f"cannot read {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
        raise TaxonomyError(f"{path}: expected a top-level 'categories' list")

    try:
        categories = [Category.model_validate(item) for item in data["categories"]]
    except ValidationError as exc:
        raise TaxonomyError(f"{path}: invalid category: {exc}") from exc

    seen: set[str] = set()
    for category in categories:
        if category.id in seen:
            raise TaxonomyError(f"{path}: duplicate category id {category.id!r}")
        seen.add(category.id)
        if category.kind is not CategoryKind.expense and category.deductible_pct != 0:
            raise TaxonomyError(f"{path}: {category.id!r} is not an expense but is deductible")

    if NEEDS_REVIEW not in seen:
        raise TaxonomyError(f"{path}: missing required category {NEEDS_REVIEW!r}")

    return Taxonomy(categories)


@lru_cache
def load_taxonomy(path: Path = DEFAULT_PATH) -> Taxonomy:
    return parse_taxonomy(path)


def get_category(category_id: str) -> Category:
    return load_taxonomy().get(category_id)


def all_categories() -> list[Category]:
    return load_taxonomy().all()


def is_valid_category(category_id: str) -> bool:
    return category_id in load_taxonomy()
