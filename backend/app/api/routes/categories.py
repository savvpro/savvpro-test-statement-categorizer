"""JSON API routes for category management (full CRUD)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.models.merchant_rule import MerchantRule
from app.models.transaction import Transaction
from app.services.category_repository import CategoryRepository

router = APIRouter(prefix="/api/categories", tags=["categories-api"])


class CreateCategoryRequest(BaseModel):
    """Payload to create a custom category."""

    name: str = Field(..., min_length=1, max_length=64, description="Unique category name")
    description: str = Field("", max_length=255, description="Optional description")


class UpdateCategoryRequest(BaseModel):
    """Payload to update a category's name or description."""

    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=255)


def _serialize(c, tx_count: int = 0, rule_count: int = 0) -> Dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "is_system_category": c.is_system_category,
        "transaction_count": tx_count,
        "rule_count": rule_count,
        "created_at": c.created_at.isoformat() if getattr(c, "created_at", None) else None,
    }


@router.get("", summary="List categories (JSON)")
def api_list_categories(db: Session = Depends(get_db_session)) -> List[Dict[str, Any]]:
    """Return all categories with transaction and rule counts."""
    repo = CategoryRepository(db)
    categories = repo.list_categories()

    # Aggregate counts efficiently
    tx_counts: Dict[int, int] = {}
    rule_counts: Dict[int, int] = {}
    for c in categories:
        tx_counts[c.id] = db.execute(
            select(func.count(Transaction.id)).where(Transaction.category_id == c.id)
        ).scalar_one()
        rule_counts[c.id] = db.execute(
            select(func.count(MerchantRule.id)).where(MerchantRule.category_id == c.id)
        ).scalar_one()

    return [_serialize(c, tx_counts.get(c.id, 0), rule_counts.get(c.id, 0)) for c in categories]


@router.get("/{category_id}", summary="Get category by ID")
def api_get_category(category_id: int, db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """Retrieve a single category by primary key."""
    repo = CategoryRepository(db)
    cat = repo.get_by_id(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    tx_count = db.execute(
        select(func.count(Transaction.id)).where(Transaction.category_id == category_id)
    ).scalar_one()
    rule_count = db.execute(
        select(func.count(MerchantRule.id)).where(MerchantRule.category_id == category_id)
    ).scalar_one()
    return _serialize(cat, tx_count, rule_count)


@router.post("", summary="Create custom category", status_code=201)
def api_create_category(
    payload: CreateCategoryRequest,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Create a new user-defined (non-system) category."""
    from app.models.category import Category

    repo = CategoryRepository(db)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name cannot be empty.")
    if repo.get_by_name(name):
        raise HTTPException(status_code=409, detail=f"Category '{name}' already exists.")

    cat = Category(name=name, description=payload.description.strip(), is_system_category=False)
    db.add(cat)
    db.flush()
    db.commit()
    return _serialize(cat)


@router.put("/{category_id}", summary="Update category name or description")
def api_update_category(
    category_id: int,
    payload: UpdateCategoryRequest,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update a category's name and/or description. System categories can only have description updated."""
    repo = CategoryRepository(db)
    cat = repo.get_by_id(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if payload.name is not None:
        if cat.is_system_category:
            raise HTTPException(
                status_code=403,
                detail="System category names cannot be changed. You may only edit the description.",
            )
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="Category name cannot be empty.")
        existing = repo.get_by_name(new_name)
        if existing and existing.id != category_id:
            raise HTTPException(status_code=409, detail=f"Category '{new_name}' already exists.")
        cat.name = new_name

    if payload.description is not None:
        cat.description = payload.description.strip()

    db.flush()
    db.commit()
    tx_count = db.execute(
        select(func.count(Transaction.id)).where(Transaction.category_id == category_id)
    ).scalar_one()
    rule_count = db.execute(
        select(func.count(MerchantRule.id)).where(MerchantRule.category_id == category_id)
    ).scalar_one()
    return _serialize(cat, tx_count, rule_count)


@router.delete("/{category_id}", summary="Delete a custom category")
def api_delete_category(
    category_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Safely delete a custom (non-system) category.

    Blocked if:
    - The category is a system category (cannot be deleted).
    - Any transactions are still assigned to this category.
    - Any merchant rules reference this category (RESTRICT FK).
    """
    repo = CategoryRepository(db)
    cat = repo.get_by_id(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.is_system_category:
        raise HTTPException(
            status_code=403,
            detail="System categories cannot be deleted.",
        )

    tx_count = db.execute(
        select(func.count(Transaction.id)).where(Transaction.category_id == category_id)
    ).scalar_one()
    if tx_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete: {tx_count} transaction(s) are still assigned to this category. "
                "Reassign them first."
            ),
        )
    rule_count = db.execute(
        select(func.count(MerchantRule.id)).where(MerchantRule.category_id == category_id)
    ).scalar_one()
    if rule_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete: {rule_count} rule(s) reference this category. "
                "Delete or reassign those rules first."
            ),
        )

    db.delete(cat)
    db.commit()
    return {"status": "ok", "deleted_category_id": category_id}

