"""FastAPI routes for the Statement Categorizer API."""

import csv
import io
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.brain.classifier import classify
from app.models import SummaryResponse, Transaction, TransactionUpdate, UploadResponse
from app.parsing.csv_parser import parse_csv
from app.store import store

router = APIRouter()

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

NON_SPENDING_CATEGORIES = {"Transfer"}


def _compute_summary(transactions: list[Transaction]) -> dict[str, float]:
    """Compute category totals from transactions.

    - Transfer excluded from spending totals
    - Refunds shown as negative spend
    - Needs Review shown separately
    """
    totals: dict[str, float] = {}
    for tx in transactions:
        totals[tx.category] = totals.get(tx.category, 0.0) + tx.amount
    return totals


@router.post("/api/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    """Upload a CSV statement and return categorized transactions."""

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a .csv file.",
        )

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB} MB.",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded.",
        )

    # Parse CSV
    parsed = parse_csv(content)
    if not parsed["transactions"] and not parsed["warnings"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid transactions found in the CSV.",
        )

    # Clear previous data
    store.clear()

    # Classify each transaction
    transactions: list[Transaction] = []
    for row in parsed["transactions"]:
        tx_id = str(uuid.uuid4())
        result = classify(
            row["description"], row["amount"], store.overrides
        )
        tx = Transaction(
            id=tx_id,
            date=row["date"],
            description=row["description"],
            amount=row["amount"],
            category=result.category,
            confidence=result.confidence,
            reason=result.reason,
            needs_review=result.needs_review,
            is_duplicate=row["is_duplicate"],
        )
        store.add(tx)
        transactions.append(tx)

    summary = _compute_summary(transactions)

    return UploadResponse(
        transactions=transactions,
        summary=summary,
        warnings=parsed["warnings"],
    )


@router.patch("/api/transactions/{tx_id}", response_model=dict)
def update_transaction(tx_id: str, update: TransactionUpdate):
    """Update a transaction's category and store a merchant override."""

    updated = store.update_category(tx_id, update.category)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {tx_id} not found.",
        )

    all_tx = store.list_all()
    summary = _compute_summary(all_tx)

    return {
        "transaction": updated,
        "summary": summary,
    }


@router.get("/api/summary", response_model=SummaryResponse)
def get_summary():
    """Get category totals (Transfer excluded from spending)."""

    transactions = store.list_all()
    totals = _compute_summary(transactions)

    spending_total = sum(
        amt for cat, amt in totals.items() if cat not in NON_SPENDING_CATEGORIES
    )
    needs_review_total = totals.get("Needs Review", 0.0)

    return SummaryResponse(
        totals=totals,
        needs_review_total=needs_review_total,
        spending_total=spending_total,
    )


@router.get("/api/export")
def export_csv():
    """Export final categorized result as CSV."""

    transactions = store.list_all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "date", "description", "amount", "category",
         "confidence", "reason", "needs_review", "is_duplicate"]
    )
    for tx in transactions:
        writer.writerow(
            [tx.id, tx.date, tx.description, tx.amount, tx.category,
             tx.confidence, tx.reason, tx.needs_review, tx.is_duplicate]
        )

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="categorized.csv"'},
    )
