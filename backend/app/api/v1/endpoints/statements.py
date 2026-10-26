from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.statement import Statement
from app.models.transaction import Transaction

router = APIRouter(prefix="/statements", tags=["statements"])
Db = Annotated[AsyncSession, Depends(get_db)]


class StatementOut(BaseModel):
    id: str
    account_id: str
    filename: str
    format: str
    period_start: str | None
    period_end: str | None
    row_count: int
    skipped_rows: list[Any]
    warnings: list[Any]
    created_at: str
    needs_review_count: int = 0

    model_config = {"from_attributes": True}


@router.get("", response_model=list[StatementOut])
async def list_statements(db: Db, account_id: str | None = None) -> list[dict[str, Any]]:
    q = select(Statement).order_by(Statement.created_at.desc())
    if account_id:
        q = q.where(Statement.account_id == account_id)
    result = await db.execute(q)
    stmts = list(result.scalars())

    out = []
    for s in stmts:
        # Count needs_review
        nr_count_result = await db.execute(
            select(Transaction).where(
                Transaction.statement_id == s.id, Transaction.status == "needs_review"
            )
        )
        nr_count = len(list(nr_count_result.scalars()))

        out.append({
            "id": s.id,
            "account_id": s.account_id,
            "filename": s.filename,
            "format": s.format,
            "period_start": s.period_start.isoformat() if s.period_start else None,
            "period_end": s.period_end.isoformat() if s.period_end else None,
            "row_count": s.row_count,
            "skipped_rows": json.loads(s.skipped_rows or "[]"),
            "warnings": json.loads(s.warnings or "[]"),
            "created_at": s.created_at.isoformat(),
            "needs_review_count": nr_count,
        })
    return out


@router.get("/{statement_id}")
async def get_statement(statement_id: str, db: Db) -> dict[str, Any]:
    stmt = await db.get(Statement, statement_id)
    if not stmt:
        raise NotFoundError("Statement", statement_id)

    txns_result = await db.execute(
        select(Transaction)
        .where(Transaction.statement_id == statement_id)
        .order_by(Transaction.posted_date.desc())
    )
    txns = list(txns_result.scalars())

    return {
        "id": stmt.id,
        "account_id": stmt.account_id,
        "filename": stmt.filename,
        "format": stmt.format,
        "period_start": stmt.period_start.isoformat() if stmt.period_start else None,
        "period_end": stmt.period_end.isoformat() if stmt.period_end else None,
        "row_count": stmt.row_count,
        "skipped_rows": json.loads(stmt.skipped_rows or "[]"),
        "warnings": json.loads(stmt.warnings or "[]"),
        "created_at": stmt.created_at.isoformat(),
        "transaction_count": len(txns),
        "needs_review_count": sum(1 for t in txns if t.status == "needs_review"),
    }


@router.delete("/{statement_id}", status_code=204)
async def delete_statement(statement_id: str, db: Db) -> None:
    stmt = await db.get(Statement, statement_id)
    if not stmt:
        raise NotFoundError("Statement", statement_id)
    # Cascade delete transactions
    txns_result = await db.execute(
        select(Transaction).where(Transaction.statement_id == statement_id)
    )
    for t in txns_result.scalars():
        await db.delete(t)
    await db.delete(stmt)
    await db.commit()
