"""JSON API routes for statements."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.services.statement_repository import StatementRepository
from app.services.transaction_repository import TransactionRepository

router = APIRouter(prefix="/api/statements", tags=["statements-api"])


@router.get("", summary="List statements (JSON)")
def api_list_statements(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Return paginated list of statements as JSON."""
    repo = StatementRepository(db)
    statements = repo.list_statements(limit=limit, offset=offset)
    return [
        {
            "id": s.id,
            "original_filename": s.original_filename,
            "status": s.status,
            "transaction_count": s.transaction_count,
            "currency": s.currency,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in statements
    ]


@router.get("/{statement_id}/transactions", summary="Transactions for a statement (JSON)")
def api_statement_transactions(
    statement_id: int,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Return transactions for a specific statement as JSON."""
    stmt_repo = StatementRepository(db)
    statement = stmt_repo.get_by_id(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    tx_repo = TransactionRepository(db)
    transactions = tx_repo.list_by_statement(statement_id, limit=limit, offset=offset)
    return [
        {
            "id": t.id,
            "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
            "original_description": t.original_description,
            "normalized_description": t.normalized_description,
            "amount": str(t.amount),
            "currency": t.currency,
            "category_id": t.category_id,
            "category_name": t.category.name if t.category else None,
            "confidence_score": t.confidence_score,
            "classification_reason": t.classification_reason,
            "review_status": t.review_status,
            "was_manually_categorized": t.was_manually_categorized,
        }
        for t in transactions
    ]


@router.get("/{statement_id}/summary", summary="Statement summary (JSON)")
def api_statement_summary(
    statement_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Return financial summary for a specific statement."""
    from decimal import Decimal
    from app.models.transaction import ReviewStatus

    stmt_repo = StatementRepository(db)
    statement = stmt_repo.get_by_id(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    tx_repo = TransactionRepository(db)
    transactions = tx_repo.list_by_statement(statement_id, limit=200, offset=0)

    total_in = Decimal("0")
    total_out = Decimal("0")
    review_count = 0
    category_totals: Dict[str, Decimal] = {}

    for t in transactions:
        cat_name = t.category.name if t.category else "Needs Review"
        # Exclude internal transfers from income/expense totals
        if cat_name in ("Internal Transfer",):
            continue
        if t.amount > 0:
            total_in += t.amount
        else:
            total_out += abs(t.amount)
        if t.review_status == ReviewStatus.PENDING:
            review_count += 1
        category_totals[cat_name] = category_totals.get(cat_name, Decimal("0")) + abs(t.amount)

    return {
        "statement_id": statement_id,
        "total_in": str(total_in),
        "total_out": str(total_out),
        "review_count": review_count,
        "category_totals": {k: str(v) for k, v in category_totals.items()},
    }
