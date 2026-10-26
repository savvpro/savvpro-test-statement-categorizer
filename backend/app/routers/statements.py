from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.parser import parse_statement
from app.services.categorizer import categorize
from app.models.transaction import (
    Transaction, TransactionUpdate, StatementResult, Category
)

router = APIRouter(prefix="/api", tags=["statements"])

# In-memory store for the session
_transactions: dict[int, Transaction] = {}


@router.post("/upload", response_model=StatementResult)
async def upload_statement(file: UploadFile = File(...)):
    global _transactions
    _transactions = {}

    try:
        rows = await parse_statement(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    transactions = []
    for idx, row in enumerate(rows):
        category, confidence = categorize(row["description"], row["amount"])
        t = Transaction(
            id=idx,
            date=row["date"],
            description=row["description"],
            amount=row["amount"],
            category=category,
            confidence=confidence,
            is_debit=row["amount"] > 0,
        )
        _transactions[idx] = t
        transactions.append(t)

    return _build_result(transactions)


@router.patch("/transactions/{transaction_id}", response_model=Transaction)
def update_transaction(transaction_id: int, update: TransactionUpdate):
    if transaction_id not in _transactions:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    _transactions[transaction_id].category = update.category
    return _transactions[transaction_id]


@router.get("/transactions", response_model=StatementResult)
def get_transactions():
    return _build_result(list(_transactions.values()))


def _build_result(transactions: list[Transaction]) -> StatementResult:
    summary: dict[str, float] = {}
    for t in transactions:
        if t.is_debit:
            summary[t.category] = summary.get(t.category, 0) + t.amount

    needs_review = sum(1 for t in transactions if t.category == Category.NEEDS_REVIEW)

    return StatementResult(
        transactions=transactions,
        summary=summary,
        total_spending=sum(summary.values()),
        needs_review_count=needs_review,
    )