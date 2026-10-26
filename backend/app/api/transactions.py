from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas import TransactionOut, TransactionUpdate, TransactionUpdateOut
from app.services import review_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.patch("/{txn_id}", response_model=TransactionUpdateOut)
def update_transaction(db: DbSession, txn_id: int, body: TransactionUpdate) -> TransactionUpdateOut:
    txn, updated = review_service.update_category(db, txn_id, body.category_id, body.remember)
    return TransactionUpdateOut(
        transaction=TransactionOut.model_validate(txn), updated_count=updated
    )
