"""JSON API routes for statement reconciliation."""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation-api"])


def _serialize_rec(rec) -> Dict[str, Any]:
    return {
        "statement_id": rec.statement_id,
        "original_filename": rec.original_filename,
        "status": rec.status,
        "currency": rec.currency,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "transaction_count": rec.transaction_count,
        "total_credits": float(rec.total_credits),
        "total_debits": float(rec.total_debits),
        "net_movement": float(rec.net_movement),
        "transfers_total": float(rec.transfers_total),
        "transfers_count": rec.transfers_count,
        "refunds_total": float(rec.refunds_total),
        "refunds_count": rec.refunds_count,
        "reversals_total": float(rec.reversals_total),
        "reversals_count": rec.reversals_count,
        "reviewed_count": rec.reviewed_count,
        "pending_count": rec.pending_count,
        "needs_review_count": rec.needs_review_count,
        "opening_balance": float(rec.opening_balance) if rec.opening_balance is not None else None,
        "closing_balance": float(rec.closing_balance) if rec.closing_balance is not None else None,
        "expected_closing_balance": (
            float(rec.expected_closing_balance)
            if rec.expected_closing_balance is not None
            else None
        ),
        "discrepancy": float(rec.discrepancy) if rec.discrepancy is not None else None,
        "is_balanced": rec.is_balanced,
    }


@router.get("", summary="List all statement reconciliations")
def api_list_reconciliations(db: Session = Depends(get_db_session)) -> List[Dict[str, Any]]:
    """Return reconciliation summaries for all imported statements."""
    svc = ReconciliationService(db)
    items = svc.reconcile_all_statements()
    return [_serialize_rec(item) for item in items]


@router.get("/{statement_id}", summary="Get statement reconciliation by ID")
def api_get_statement_reconciliation(
    statement_id: int,
    opening_balance: Optional[float] = Query(None, description="Optional opening statement balance"),
    closing_balance: Optional[float] = Query(None, description="Optional closing statement balance"),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Return reconciliation summary for a specific statement, with optional balance check."""
    svc = ReconciliationService(db)
    open_dec = Decimal(str(opening_balance)) if opening_balance is not None else None
    close_dec = Decimal(str(closing_balance)) if closing_balance is not None else None

    rec = svc.reconcile_statement(statement_id, opening_balance=open_dec, closing_balance=close_dec)
    if not rec:
        raise HTTPException(status_code=404, detail="Statement not found")

    return _serialize_rec(rec)
