"""Category persistence and seeding repository."""

from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import DEFAULT_CATEGORIES


class CategoryRepository:
    """Repository managing category persistence and safe idempotent seeding."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def seed_default_categories(self) -> int:
        """Seed the 16 core categories from the Phase 1 source of truth.

        Idempotent: Skips categories that already exist in the database.
        Never overwrites existing or user-defined categories.

        Returns:
            The number of newly created category records.
        """
        existing_categories = {c.name: c for c in self.list_categories()}
        new_count = 0

        for cat_enum, meta in DEFAULT_CATEGORIES.items():
            if meta.name not in existing_categories:
                new_category = Category(
                    name=meta.name,
                    description=meta.description,
                    is_system_category=meta.is_system_category,
                )
                self.session.add(new_category)
                new_count += 1

        if new_count > 0:
            self.session.flush()

        return new_count

    def get_by_name(self, name: str) -> Optional[Category]:
        """Retrieve a category by exact name."""
        stmt = select(Category).where(Category.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Retrieve a category by primary key ID."""
        return self.session.get(Category, category_id)

    def list_categories(self) -> List[Category]:
        """Retrieve all categories ordered by ID."""
        stmt = select(Category).order_by(Category.id)
        return list(self.session.execute(stmt).scalars().all())

    def get_category_map(self) -> Dict[str, Category]:
        """Return a mapping of category name to Category instance."""
        return {c.name: c for c in self.list_categories()}
