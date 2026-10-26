
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Statement, Transaction

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/")
def get_transactions(
    statement_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Return transactions for a statement, defaulting to the latest upload."""
    if statement_id is None:
        statement = (
            db.query(Statement)
            .order_by(Statement.id.desc())
            .first()
        )
        if statement is None:
            return {"count": 0, "statement_id": None, "transactions": []}
        statement_id = statement.id
    elif db.query(Statement.id).filter(Statement.id == statement_id).first() is None:
        raise HTTPException(status_code=404, detail="Statement not found.")

    transactions = (
        db.query(Transaction)
        .filter(Transaction.statement_id == statement_id)
        .order_by(Transaction.id)
        .all()
    )

    return {
        "count": len(transactions),
        "statement_id": statement_id,
        "transactions": [
            {
                "id": transaction.id,
                "statement_id": transaction.statement_id,
                "date": transaction.date,
                "description": transaction.description,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "balance": transaction.balance,
                "source_row": transaction.source_row,
                "category": transaction.category,
                "status": transaction.status,
                "reason": transaction.reason,
                "confidence": transaction.confidence,
                "source": transaction.source,
                "corrected_category": transaction.corrected_category,
            }
            for transaction in transactions
        ],
    }


@router.patch("/{transaction_id}/category")
def correct_category(
    transaction_id: int,
    category: str,
    db: Session = Depends(get_db),
):
    """Correct a transaction category and mark it as reviewed."""
    category = category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="Category cannot be empty.")

    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    transaction.corrected_category = category
    transaction.category = category
    transaction.status = "reviewed"
    transaction.reason = "Category manually corrected by user."
    transaction.source = "manual"

    db.commit()
    db.refresh(transaction)

    return {
        "success": True,
        "message": "Transaction category updated.",
        "transaction": {
            "id": transaction.id,
            "description": transaction.description,
            "category": transaction.category,
            "status": transaction.status,
            "corrected_category": transaction.corrected_category,
        },
    }
