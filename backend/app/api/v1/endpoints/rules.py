from __future__ import annotations

import contextlib
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.rule import Rule
from app.models.transaction import Transaction

router = APIRouter(prefix="/rules", tags=["rules"])
Db = Annotated[AsyncSession, Depends(get_db)]


class RuleCreate(BaseModel):
    match_type: str
    pattern: str
    category_id: str | None = None
    kind: str | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    account_id: str | None = None
    priority: int = 0


class RuleUpdate(BaseModel):
    match_type: str | None = None
    pattern: str | None = None
    category_id: str | None = None
    kind: str | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    account_id: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class RuleOut(BaseModel):
    id: str
    match_type: str
    pattern: str
    category_id: str | None
    kind: str | None
    amount_min: int | None
    amount_max: int | None
    account_id: str | None
    priority: int
    enabled: bool
    hit_count: int
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[RuleOut])
async def list_rules(db: Db) -> list[Rule]:
    result = await db.execute(select(Rule).order_by(Rule.priority.desc()))
    return list(result.scalars())


@router.post("", response_model=RuleOut, status_code=201)
async def create_rule(body: RuleCreate, db: Db) -> Rule:
    rule = Rule(id=str(uuid.uuid4()), **body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: str, body: RuleUpdate, db: Db) -> Rule:
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise NotFoundError("Rule", rule_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        # match_type, pattern, priority and enabled are non-nullable columns
        if v is None and k in ("match_type", "pattern", "priority", "enabled"):
            continue
        setattr(rule, k, v)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, db: Db) -> None:
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise NotFoundError("Rule", rule_id)
    await db.delete(rule)
    await db.commit()


@router.post("/preview")
async def preview_rule(body: RuleCreate, db: Db) -> dict[str, Any]:
    """Show which existing transactions would be matched by this rule."""
    import re as _re

    result = await db.execute(select(Transaction))
    matched_ids: list[str] = []
    for t in result.scalars():
        merchant = t.merchant
        match_type = body.match_type
        pattern = body.pattern or ""
        matched = False
        if match_type == "merchant_exact":
            matched = merchant.upper() == pattern.upper()
        elif match_type == "contains":
            matched = pattern.upper() in merchant.upper()
        elif match_type == "regex":
            with contextlib.suppress(_re.error):
                matched = bool(_re.search(pattern, merchant, _re.I))
        if matched:
            matched_ids.append(t.id)

    return {"match_count": len(matched_ids), "matched_ids": matched_ids[:50]}
