"""
Transactions API – list, patch, bulk update.
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.brain.categories import CATEGORIES, get_deductible_pct
from app.db import get_session
from app.models import MatchType, Transaction, TxnStatus, UserRule
from app.schemas import (
    BulkPatch,
    PaginatedTransactions,
    TransactionOut,
    TransactionPatch,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=PaginatedTransactions)
def list_transactions(
    statement_id: int,
    status: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """
    List transactions for a statement with optional filters.

    Filters:
     - status: auto, suggested, needs_review, user_confirmed
     - category: any category key
     - q: free-text search on raw_description / merchant_key
    """
    query = select(Transaction).where(Transaction.statement_id == statement_id)

    if status:
        if status == "excluded":
            # Special filter for excluded categories
            from app.brain.categories import EXCLUDED_KEYS
            query = query.where(Transaction.category.in_(EXCLUDED_KEYS))
        else:
            query = query.where(Transaction.status == status)

    if category:
        query = query.where(Transaction.category == category)

    if q:
        search = f"%{q}%"
        query = query.where(
            Transaction.raw_description.ilike(search)
            | Transaction.merchant_key.ilike(search)
        )

    # Count total before pagination
    count_txns = session.exec(query).all()
    total = len(count_txns)

    # Apply pagination and ordering
    query = query.order_by(Transaction.posted_date, Transaction.row_index)
    query = query.offset((page - 1) * page_size).limit(page_size)
    txns = session.exec(query).all()

    items = []
    for t in txns:
        out = TransactionOut.model_validate(t)
        out.flags = t.flags  # use the property
        items.append(out)

    return PaginatedTransactions(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{txn_id}", response_model=TransactionOut)
def patch_transaction(
    txn_id: int,
    body: TransactionPatch,
    session: Session = Depends(get_session),
):
    """
    Update a transaction's category or note.

    If save_rule is True, creates a UserRule for the merchant_key.
    """
    txn = session.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")

    if body.category is not None:
        if body.category not in CATEGORIES:
            raise HTTPException(400, f"Unknown category: {body.category}")
        txn.category = body.category
        txn.confidence = 1.0
        txn.status = TxnStatus.USER_CONFIRMED
        txn.reason = f"User confirmed: {body.category}"
        txn.deductible_pct = get_deductible_pct(body.category)

    if body.user_note is not None:
        txn.user_note = body.user_note

    # Save as rule
    if body.save_rule and body.category and txn.merchant_key:
        # Check if rule already exists
        existing_rule = session.exec(
            select(UserRule).where(
                UserRule.pattern == txn.merchant_key,
                UserRule.match_type == MatchType.EXACT,
            )
        ).first()

        if existing_rule:
            existing_rule.category = body.category
            txn.rule_id = existing_rule.id
        else:
            rule = UserRule(
                match_type=MatchType.EXACT,
                pattern=txn.merchant_key,
                category=body.category,
                hit_count=1,
            )
            session.add(rule)
            session.flush()
            txn.rule_id = rule.id

    session.commit()
    session.refresh(txn)

    out = TransactionOut.model_validate(txn)
    out.flags = txn.flags
    return out


@router.post("/bulk", response_model=list[TransactionOut])
def bulk_update(body: BulkPatch, session: Session = Depends(get_session)):
    """Apply a category to multiple transactions at once."""
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category: {body.category}")

    txns = session.exec(
        select(Transaction).where(Transaction.id.in_(body.ids))
    ).all()

    if not txns:
        raise HTTPException(404, "No transactions found")

    deductible_pct = get_deductible_pct(body.category)
    rule_id = None

    # Optionally save a rule for the first merchant_key
    if body.save_rule and txns:
        merchant = txns[0].merchant_key
        if merchant:
            existing_rule = session.exec(
                select(UserRule).where(
                    UserRule.pattern == merchant,
                    UserRule.match_type == MatchType.EXACT,
                )
            ).first()
            if existing_rule:
                existing_rule.category = body.category
                rule_id = existing_rule.id
            else:
                rule = UserRule(
                    match_type=MatchType.EXACT,
                    pattern=merchant,
                    category=body.category,
                    hit_count=len(txns),
                )
                session.add(rule)
                session.flush()
                rule_id = rule.id

    for t in txns:
        t.category = body.category
        t.confidence = 1.0
        t.status = TxnStatus.USER_CONFIRMED
        t.reason = f"Bulk update: {body.category}"
        t.deductible_pct = deductible_pct
        if rule_id:
            t.rule_id = rule_id

    session.commit()

    results = []
    for t in txns:
        session.refresh(t)
        out = TransactionOut.model_validate(t)
        out.flags = t.flags
        results.append(out)
    return results
