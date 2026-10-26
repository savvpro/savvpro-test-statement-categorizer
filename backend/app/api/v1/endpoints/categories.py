from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.category import Category
from app.models.transaction import Transaction

router = APIRouter(prefix="/categories", tags=["categories"])
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("")
async def list_categories(db: Db, with_totals: bool = False, year: int | None = None) -> list[dict[str, Any]]:
    result = await db.execute(select(Category).order_by(Category.group, Category.name))
    cats = list(result.scalars())

    out = []
    for c in cats:
        item: dict[str, Any] = {
            "id": c.id,
            "name": c.name,
            "group": c.group,
            "schedule_c_line": c.schedule_c_line,
            "deductible_pct": c.deductible_pct,
            "color": c.color,
            "icon": c.icon,
            "description": c.description,
            "is_system": c.is_system,
        }
        if with_totals:
            q = select(func.sum(Transaction.amount_cents)).where(
                Transaction.category_id == c.id,
                Transaction.status != "needs_review",
            )
            if year:
                q = q.where(
                    Transaction.posted_date >= f"{year}-01-01",
                    Transaction.posted_date <= f"{year}-12-31",
                )
            total = await db.scalar(q) or 0
            item["total_cents"] = total
        out.append(item)
    return out
