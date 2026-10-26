"""
FastAPI backend for the Statement Categorizer.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .categorizer import ALL_CATEGORIES, categorize_batch
from .parsers import parse_csv


app = FastAPI(
    title="Statement Categorizer",
    description="Rule-based bank/credit-card statement categorizer for freelancers",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TransactionUpdate(BaseModel):
    index: int
    category: str


class CategorizeResponse(BaseModel):
    transactions: list[dict[str, Any]]
    summary: dict[str, float]
    total_transactions: int
    needs_review_count: int


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def list_categories():
    return {"categories": ALL_CATEGORIES}


@app.post("/api/categorize", response_model=CategorizeResponse)
async def categorize_statement(file: UploadFile = File(...)):
    """
    Upload a CSV statement and receive categorized transactions + summary.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported in this version",
        )

    try:
        content = await file.read()
        raw_transactions = parse_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    categorized = categorize_batch(raw_transactions)

    # Build summary (sum of amounts per category)
    # Note: expenses are usually negative; we keep the sign so totals are meaningful
    summary: dict[str, float] = {}
    needs_review_count = 0

    for tx in categorized:
        cat = tx["category"]
        summary[cat] = summary.get(cat, 0.0) + tx["amount"]
        if cat == "Needs Review":
            needs_review_count += 1

    # Round for display
    summary = {k: round(v, 2) for k, v in summary.items()}

    return CategorizeResponse(
        transactions=categorized,
        summary=summary,
        total_transactions=len(categorized),
        needs_review_count=needs_review_count,
    )


@app.post("/api/update-category")
def update_category(payload: TransactionUpdate):
    """
    Placeholder endpoint for future persistence of user corrections.
    In this demo the frontend keeps state client-side.
    """
    if payload.category not in ALL_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    return {"ok": True, "index": payload.index, "category": payload.category}
