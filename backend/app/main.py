"""
main.py - FastAPI app

Kept the API surface small - just upload, override, and summary.
Session state is in-memory for now (keyed by filename). Good enough for
a single-user demo but would need Redis or a proper DB for production.
"""

from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .categorizer import Category, categorize
from .models import (
    CategorizedTransaction,
    OverrideRequest,
    SummaryItem,
    SummaryResponse,
    UploadResponse,
)
from .parser import parse_statement

app = FastAPI(
    title="Statement Categorizer",
    description="Upload a bank or credit-card statement and get every transaction auto-categorised.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store keyed by filename. Fine for a demo, but in production
# this would be a proper DB with user sessions and auth.
# TODO: if time permits, swap this out for SQLite at least
_sessions: dict[str, list[CategorizedTransaction]] = {}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Upload & categorize
# ---------------------------------------------------------------------------


@app.post("/upload", response_model=UploadResponse)
async def upload_statement(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a CSV or OFX/QFX statement.
    Returns every transaction with its auto-assigned category.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed_extensions = {".csv", ".ofx", ".qfx"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Please upload CSV or OFX/QFX.",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB guard
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    try:
        transactions = parse_statement(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not transactions:
        raise HTTPException(status_code=422, detail="No transactions found in the file")

    categorized: list[CategorizedTransaction] = []
    for txn in transactions:
        result = categorize(txn.description, txn.amount)
        categorized.append(
            CategorizedTransaction(
                id=txn.id,
                date=txn.date,
                description=txn.description,
                amount=txn.amount,
                category=result.category.value,
                confidence=round(result.confidence, 4),
                reason=result.reason,
                is_review=result.is_review,
            )
        )

    # Store in session keyed by filename (demo simplification)
    session_key = file.filename
    _sessions[session_key] = categorized

    return UploadResponse(
        filename=file.filename,
        total=len(categorized),
        transactions=categorized,
    )


# ---------------------------------------------------------------------------
# Override a single transaction's category
# ---------------------------------------------------------------------------


@app.patch("/transactions/{session_id}/{transaction_id}", response_model=CategorizedTransaction)
def override_category(
    session_id: str,
    transaction_id: str,
    body: OverrideRequest,
) -> CategorizedTransaction:
    """
    Manually override the category for a single transaction.
    Sets is_review = False and records the original auto-assigned category.
    """
    # Validate category value
    valid_categories = {c.value for c in Category}
    if body.category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Choose from: {sorted(valid_categories)}",
        )

    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Please re-upload the file.")

    for txn in session:
        if txn.id == transaction_id:
            txn.original_category = txn.category
            txn.category = body.category
            txn.is_review = False
            txn.reason = "Manually overridden"
            txn.confidence = 1.0
            return txn

    raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found")


# ---------------------------------------------------------------------------
# Category summary
# ---------------------------------------------------------------------------


@app.get("/sessions/{session_id}/summary", response_model=SummaryResponse)
def get_summary(session_id: str) -> SummaryResponse:
    """Return per-category totals and counts for the uploaded statement."""
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Please re-upload the file.")

    totals: dict[str, dict] = {}
    for txn in session:
        cat = txn.category
        if cat not in totals:
            totals[cat] = {"count": 0, "total": 0.0}
        totals[cat]["count"] += 1
        totals[cat]["total"] += txn.amount or 0.0

    summary = [
        SummaryItem(
            category=cat,
            count=data["count"],
            total=round(data["total"], 2),
        )
        for cat, data in sorted(totals.items())
    ]

    return SummaryResponse(summary=summary)


# ---------------------------------------------------------------------------
# Available categories (for the frontend dropdown)
# ---------------------------------------------------------------------------


@app.get("/categories")
def list_categories() -> dict:
    return {"categories": [c.value for c in Category]}
