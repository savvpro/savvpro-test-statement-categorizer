"""Demo endpoints – seed / reset fake data for reviewers."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.account import Account
from app.models.correction import Correction
from app.models.import_draft import ImportDraft
from app.models.rule import Rule
from app.models.statement import Statement
from app.models.transaction import Transaction
from app.seed import seed_categories, seed_demo_data

router = APIRouter(prefix="/demo", tags=["demo"])
Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("/seed", status_code=201)
async def seed(db: Db) -> dict[str, Any]:
    """Seed categories + demo accounts + transactions."""
    await seed_categories(db)
    result = await seed_demo_data(db)
    return result


@router.post("/reset", status_code=200)
async def reset(db: Db) -> dict[str, Any]:
    """Wipe all user data (demo reset). Categories are re-seeded."""
    for model in [Correction, Transaction, Statement, ImportDraft, Rule, Account]:
        await db.execute(delete(model))
    # Keep categories (system-seeded)
    await db.commit()
    await seed_categories(db)
    return {"status": "reset complete"}
