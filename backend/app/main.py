"""
FastAPI application layer for Statement Categorizer.
Exposes REST endpoints for file upload, transaction re-calculation,
category definitions, and sample demo data.
"""

import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models.transaction import (
    CategorizeResponse,
    RecalculateRequest,
    TaxSummary,
)
from app.services.parser import parse_csv
from app.brain.classifier import StatementBrain
from app.brain.tax_summary import calculate_tax_summary
from app.brain.categories import TAX_CATEGORIES

app = FastAPI(
    title="Statement Categorizer API",
    version="1.0.0",
    description="Deterministic IRS Schedule C Statement Categorizer for Freelance Tech Consultants",
)

# CORS middleware configuration allowing Vite and frontend clients
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"


@app.get("/", tags=["Health"])
async def root():
    """Service health check."""
    return {
        "status": "online",
        "service": "Statement Categorizer API",
        "version": "1.0.0",
        "endpoints": ["/api/upload", "/api/recalculate", "/api/categories", "/api/sample"],
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """API health status endpoint."""
    return {"status": "healthy"}


@app.post(
    "/api/upload",
    response_model=CategorizeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Categorization"],
    summary="Upload and categorize bank/credit card CSV statement",
)
async def upload_statement(file: UploadFile = File(...)):
    """
    Accepts a multipart CSV bank statement upload, parses rows, runs
    deterministic classification rules, and aggregates IRS Schedule C tax summaries.
    """
    filename = file.filename or "statement.csv"

    # Validate file extension
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type for '{filename}'. Only .csv files are supported.",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    try:
        raw_txs, warnings = parse_csv(content, filename)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV format error: {str(ve)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while parsing the CSV: {str(e)}",
        )

    # Classify all transactions through deterministic brain
    brain = StatementBrain()
    is_credit = "credit" in filename.lower() or "card" in filename.lower()
    categorized_txs = [brain.categorize_transaction(tx, is_credit_statement=is_credit) for tx in raw_txs]

    # Calculate IRS Schedule C tax summary
    summary = calculate_tax_summary(categorized_txs)

    return CategorizeResponse(
        filename=filename,
        parsed_count=len(categorized_txs),
        warnings=warnings,
        transactions=categorized_txs,
        summary=summary,
    )


@app.post(
    "/api/recalculate",
    response_model=TaxSummary,
    status_code=status.HTTP_200_OK,
    tags=["Categorization"],
    summary="Recalculate tax summary from modified transactions",
)
async def recalculate_summary(request: RecalculateRequest):
    """
    Recalculates gross income, deductible expenses, net profit, and tax savings
    when the user edits transaction categories, status, or amounts in the frontend.
    """
    try:
        updated_summary = calculate_tax_summary(request.transactions)
        return updated_summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate tax summary: {str(e)}",
        )


@app.get(
    "/api/categories",
    tags=["Metadata"],
    summary="Get all IRS Schedule C tax category definitions and metadata",
)
async def get_categories():
    """
    Returns the comprehensive TAX_CATEGORIES map including Schedule C line,
    deductible percentage, UI hex color, and descriptions.
    """
    return TAX_CATEGORIES


@app.get(
    "/api/sample",
    response_model=CategorizeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Categorization"],
    summary="Get pre-categorized demo sample statement",
)
async def get_sample_statement():
    """
    Loads the built-in sample statement from disk, parses and categorizes it,
    providing instant demo capability without requiring a user file upload.
    """
    sample_file = SAMPLE_DATA_DIR / "sample_statement.csv"
    if not sample_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample statement file not found on server.",
        )

    try:
        content = sample_file.read_bytes()
        raw_txs, warnings = parse_csv(content, "sample_statement.csv")
        brain = StatementBrain()
        categorized_txs = [brain.categorize_transaction(tx) for tx in raw_txs]
        summary = calculate_tax_summary(categorized_txs)

        return CategorizeResponse(
            filename="sample_statement.csv",
            parsed_count=len(categorized_txs),
            warnings=warnings,
            transactions=categorized_txs,
            summary=summary,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load sample statement: {str(e)}",
        )
