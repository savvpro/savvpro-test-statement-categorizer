from __future__ import annotations

import csv
import io
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.correction import Correction
from app.models.rule import Rule
from app.models.transaction import Transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])
Db = Annotated[AsyncSession, Depends(get_db)]


def _txn_to_dict(t: Transaction) -> dict[str, Any]:
    return {
        "id": t.id,
        "statement_id": t.statement_id,
        "account_id": t.account_id,
        "posted_date": t.posted_date.isoformat(),
        "description_raw": t.description_raw,
        "merchant": t.merchant,
        "amount_cents": t.amount_cents,
        "kind": t.kind,
        "category_id": t.category_id,
        "status": t.status,
        "confidence": t.confidence,
        "reasons": json.loads(t.reasons or "[]"),
        "review_reason": t.review_reason,
        "fingerprint": t.fingerprint,
        "linked_txn_id": t.linked_txn_id,
        "note": t.note,
        "deductible_pct_override": t.deductible_pct_override,
        "created_at": t.created_at.isoformat(),
    }


@router.get("")
async def list_transactions(
    db: Db,
    account_id: str | None = None,
    statement_id: str | None = None,
    status: str | None = None,
    category_id: str | None = None,
    kind: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    q = select(Transaction)
    filters = []
    if account_id:
        filters.append(Transaction.account_id == account_id)
    if statement_id:
        filters.append(Transaction.statement_id == statement_id)
    if status:
        filters.append(Transaction.status == status)
    if category_id:
        filters.append(Transaction.category_id == category_id)
    if kind:
        filters.append(Transaction.kind == kind)
    if search:
        filters.append(
            or_(
                Transaction.description_raw.ilike(f"%{search}%"),
                Transaction.merchant.ilike(f"%{search}%"),
            )
        )
    if date_from:
        filters.append(Transaction.posted_date >= date_from)
    if date_to:
        filters.append(Transaction.posted_date <= date_to)
    if filters:
        q = q.where(and_(*filters))

    # Count total
    count_q = select(Transaction).where(and_(*filters)) if filters else select(Transaction)
    total_result = await db.execute(count_q)
    total = len(list(total_result.scalars()))

    q = q.order_by(Transaction.posted_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    rows = [_txn_to_dict(t) for t in result.scalars()]

    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/export.csv")
async def export_csv(
    db: Db,
    account_id: str | None = None,
    year: int | None = None,
) -> Response:
    q = select(Transaction)
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if year:
        q = q.where(
            Transaction.posted_date >= f"{year}-01-01",
            Transaction.posted_date <= f"{year}-12-31",
        )
    result = await db.execute(q.order_by(Transaction.posted_date))
    txns = list(result.scalars())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Description", "Merchant", "Amount", "Kind", "Category",
                     "Status", "Confidence", "Note"])
    for t in txns:
        # CSV-injection safe: prefix with ' if starts with = + - @
        def safe(v: str) -> str:
            v = str(v)
            return "'" + v if v[:1] in ("=", "+", "-", "@") else v

        writer.writerow([
            t.posted_date.isoformat(),
            safe(t.description_raw),
            safe(t.merchant),
            f"{t.amount_cents / 100:.2f}",
            t.kind,
            t.category_id or "",
            t.status,
            f"{t.confidence:.2f}",
            safe(t.note or ""),
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@router.get("/{txn_id}")
async def get_transaction(txn_id: str, db: Db) -> dict[str, Any]:
    t = await db.get(Transaction, txn_id)
    if not t:
        raise NotFoundError("Transaction", txn_id)
    return _txn_to_dict(t)


class TxnUpdate(BaseModel):
    category_id: str | None = None
    status: str | None = None
    note: str | None = None
    deductible_pct_override: int | None = None
    apply_to_similar: bool = False
    create_rule: bool = False


@router.patch("/{txn_id}")
async def update_transaction(txn_id: str, body: TxnUpdate, db: Db) -> dict[str, Any]:
    t = await db.get(Transaction, txn_id)
    if not t:
        raise NotFoundError("Transaction", txn_id)

    # Snapshot for audit
    before = _txn_to_dict(t)

    if body.category_id is not None:
        t.category_id = body.category_id
    if body.status is not None:
        t.status = body.status
    if body.note is not None:
        t.note = body.note
    if body.deductible_pct_override is not None:
        t.deductible_pct_override = body.deductible_pct_override

    # If confirming, mark as confirmed
    if body.status == "confirmed" or body.category_id:
        t.status = "confirmed"

    after = _txn_to_dict(t)

    # Save correction audit
    corr = Correction(
        transaction_id=txn_id,
        before=json.dumps(before),
        after=json.dumps(after),
    )
    db.add(corr)

    # Apply to similar
    if body.apply_to_similar and body.category_id:
        similar_result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.merchant == t.merchant,
                    Transaction.id != txn_id,
                    Transaction.status != "confirmed",
                )
            )
        )
        for sim in similar_result.scalars():
            sim.category_id = body.category_id
            sim.status = "confirmed"

    # Create rule
    if body.create_rule and body.category_id:
        rule = Rule(
            match_type="merchant_exact",
            pattern=t.merchant,
            category_id=body.category_id,
            source="correction",
            priority=10,
        )
        db.add(rule)

    await db.commit()
    await db.refresh(t)
    return _txn_to_dict(t)


class BulkUpdate(BaseModel):
    ids: list[str]
    category_id: str | None = None
    status: str | None = None


@router.post("/bulk")
async def bulk_update(body: BulkUpdate, db: Db) -> dict[str, Any]:
    updated = 0
    for txn_id in body.ids:
        t = await db.get(Transaction, txn_id)
        if t:
            if body.category_id:
                t.category_id = body.category_id
                t.status = "confirmed"
            if body.status:
                t.status = body.status
            updated += 1
    await db.commit()
    return {"updated": updated}


@router.post("/{txn_id}/undo")
async def undo_transaction(txn_id: str, db: Db) -> dict[str, Any]:
    """Revert to the previous correction state."""
    result = await db.execute(
        select(Correction)
        .where(Correction.transaction_id == txn_id)
        .order_by(Correction.created_at.desc())
        .limit(1)
    )
    corr = result.scalar_one_or_none()
    if not corr:
        raise NotFoundError("Correction", txn_id)

    t = await db.get(Transaction, txn_id)
    if not t:
        raise NotFoundError("Transaction", txn_id)

    prev = json.loads(corr.before)
    t.category_id = prev.get("category_id")
    t.status = prev.get("status", "auto")
    t.note = prev.get("note", "")
    await db.delete(corr)
    await db.commit()
    await db.refresh(t)
    return _txn_to_dict(t)
