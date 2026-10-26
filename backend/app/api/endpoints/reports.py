
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Statement
from app.services.report_service import generate_summary

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary")
def get_summary(
    statement_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Return a financial summary for one statement."""
    if statement_id is not None:
        exists = (
            db.query(Statement.id)
            .filter(Statement.id == statement_id)
            .first()
        )
        if exists is None:
            raise HTTPException(status_code=404, detail="Statement not found.")

    return generate_summary(db, statement_id)
