from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.transactions import _txn_to_dict
from app.core.db import get_db
from app.models.transaction import Transaction

router = APIRouter(prefix="/review", tags=["review"])
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/queue")
async def get_review_queue(
    db: Db,
    account_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    q = select(Transaction).where(Transaction.status == "needs_review")
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    q = q.order_by(Transaction.posted_date.desc()).limit(limit)
    result = await db.execute(q)
    items = [_txn_to_dict(t) for t in result.scalars()]
    return {"items": items, "total": len(items)}
