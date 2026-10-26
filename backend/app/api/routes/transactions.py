"""JSON API routes for transaction management."""

import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.models.transaction import ReviewStatus, Transaction
from app.models.classification_event import ClassificationEventType
from app.services.dashboard_service import parse_date_range
from app.services.transaction_repository import TransactionRepository
from app.services.category_repository import CategoryRepository

router = APIRouter(prefix="/api/transactions", tags=["transactions-api"])


class TransactionPatchRequest(BaseModel):
    """Payload for updating a transaction's category."""

    category_id: int
    reason: Optional[str] = "Manual correction by user"


def _serialize_transaction(tx: Transaction) -> Dict[str, Any]:
    """Helper to serialize a Transaction model to a dictionary."""
    events = []
    if hasattr(tx, "classification_events") and tx.classification_events:
        for ev in tx.classification_events:
            events.append(
                {
                    "id": ev.id,
                    "event_type": ev.event_type,
                    "previous_category_id": ev.previous_category_id,
                    "previous_category_name": (
                        ev.previous_category.name if ev.previous_category else None
                    ),
                    "new_category_id": ev.new_category_id,
                    "new_category_name": ev.new_category.name if ev.new_category else None,
                    "reason": ev.reason,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
            )

    return {
        "id": tx.id,
        "statement_id": tx.statement_id,
        "statement_filename": tx.statement.original_filename if tx.statement else None,
        "transaction_date": (
            tx.transaction_date.isoformat() if tx.transaction_date else None
        ),
        "original_description": tx.original_description,
        "normalized_description": tx.normalized_description,
        "amount": float(tx.amount),
        "currency": tx.currency,
        "category_id": tx.category_id,
        "category_name": tx.category.name if tx.category else "Needs Review",
        "confidence_score": tx.confidence_score,
        "classification_reason": tx.classification_reason,
        "review_status": tx.review_status,
        "was_manually_categorized": tx.was_manually_categorized,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "updated_at": tx.updated_at.isoformat() if tx.updated_at else None,
        "classification_events": events,
    }


@router.get("", summary="List transactions with filters and pagination")
def list_transactions(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    tx_type: Optional[str] = None,
    statement_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = Query("date", description="Sort field"),
    sort_dir: str = Query("desc", description="Sort direction ('asc' or 'desc')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Retrieve transactions filtered by search, category, status, type, and date bounds."""
    s_date, e_date, date_err = parse_date_range(start_date, end_date)
    if date_err:
        raise HTTPException(status_code=400, detail=date_err)

    tx_repo = TransactionRepository(db)
    items, total = tx_repo.search_and_filter(
        q=q,
        category_id=category_id,
        status=status,
        tx_type=tx_type,
        statement_id=statement_id,
        start_date=s_date,
        end_date=e_date,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return {
        "items": [_serialize_transaction(t) for t in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{transaction_id}", summary="Get transaction by ID")
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Retrieve complete transaction details by primary key."""
    if transaction_id <= 0:
        raise HTTPException(status_code=404, detail="Invalid transaction ID")

    tx_repo = TransactionRepository(db)
    tx = tx_repo.get_by_id(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return _serialize_transaction(tx)


@router.patch("/{transaction_id}", summary="Update transaction category")
def patch_transaction(
    transaction_id: int,
    payload: TransactionPatchRequest,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Manually reassign a transaction category and record the correction event."""
    tx_repo = TransactionRepository(db)
    cat_repo = CategoryRepository(db)

    tx = db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Validate target category
    new_cat = cat_repo.get_by_id(payload.category_id)
    if not new_cat:
        raise HTTPException(status_code=404, detail="Category not found")

    old_category_id = tx.category_id

    # Apply correction
    tx.category_id = payload.category_id
    tx.was_manually_categorized = True
    tx.review_status = ReviewStatus.REVIEWED

    # Record audit event
    tx_repo.record_classification_event(
        transaction_id=tx.id,
        new_category_id=payload.category_id,
        event_type=ClassificationEventType.MANUAL_OVERRIDE,
        previous_category_id=old_category_id,
        reason=payload.reason,
    )

    db.flush()

    return {
        "id": tx.id,
        "category_id": tx.category_id,
        "category_name": new_cat.name,
        "review_status": tx.review_status,
        "was_manually_categorized": tx.was_manually_categorized,
    }
