from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas import CorrectionIn, CorrectionOut
from app.services.corrections import correct_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.patch("/{transaction_id}", response_model=CorrectionOut)
def correct(transaction_id: int, body: CorrectionIn, db: DbSession) -> CorrectionOut:
    return correct_transaction(db, transaction_id, body.category, body.kind, body.remember)
