"""
FastAPI application – Statement Categorizer API.

Endpoints:
  GET  /health                       → Health check
  POST /api/statements/parse         → Upload & categorize a CSV file
  POST /api/transactions/recalculate → Recalculate summary after user edits
  POST /api/transactions/correct     → Dedicated single-transaction correction endpoint
  GET  /api/demo                     → Return sample data for demo/testing
"""

import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.parser import parse_csv
from backend.categorizer import categorize_transactions
from backend.summaries import compute_summary
from backend.models import (
    ParseResponse, RecalculateRequest, FinancialSummary,
    TransactionCorrectionRequest, ReviewStatus,
)

app = FastAPI(
    title="Statement Categorizer API",
    description="Upload bank/credit card statements and get automatic categorization.",
    version="1.1.0",
)

# CORS – Configurable via CORS_ORIGINS environment variable
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fallback sample statement data embedded directly to guarantee availability
EMBEDDED_SAMPLE_CSV = """Date,Description,Amount
2024-01-03,ACME CORP - INVOICE 1042,5000.00
2024-01-05,ADOBE CREATIVE CLOUD,-54.99
2024-01-06,UBER *TRIP 8812,-32.50
2024-01-07,STAPLES OFFICE SUPPLIES,-89.75
2024-01-08,TRANSFER TO SAVINGS,-500.00
2024-01-10,JOES CAFE 9921,-18.40
2024-01-10,JOES CAFE 9921,-18.40
2024-01-12,PAYPAL *FREELANDESIGN,3200.00
2024-01-14,AMAZON WEB SERVICES,-149.00
2024-01-15,GOOGLE ADS,-250.00
2024-01-16,REFUND - ADOBE CREATIVE CLOUD,54.99
2024-01-17,WIX PREMIUM PLAN,-16.00
2024-01-18,DELTA AIR LINES,-387.20
2024-01-19,MARRIOTT HOTELS,-212.00
2024-01-20,CLIENT PAYMENT - WEBFLOW PROJECT,1800.00
2024-01-21,STRIPE PROCESSING FEE,-45.00
2024-01-22,TRANSFER FROM CHECKING,300.00
2024-01-23,ATM WITHDRAWAL,-200.00
2024-01-24,CANVA PRO SUBSCRIPTION,-12.99
2024-01-25,INTEREST CHARGE,-3.42
2024-01-26,COSTCO WHOLESALE,-67.80
2024-01-27,PAYMENT RECEIVED - THANK YOU,2500.00
2024-01-28,REFUND - AMAZON MARKETPLACE,29.99
2024-01-29,VENMO TRANSFER,-150.00
2024-01-30,FIGMA PROFESSIONAL,-15.00
2024-01-31,LATE PAYMENT FEE,-35.00
"""


@app.get("/health")
def health():
    return {"status": "ok", "service": "statement-categorizer-api", "version": "1.1.0"}


@app.post("/api/statements/parse", response_model=ParseResponse)
async def parse_statement(file: UploadFile = File(...)):
    """
    Upload a CSV file. Returns categorized transactions and a financial summary.
    """
    if file.content_type and file.content_type not in (
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
        "text/plain",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Please upload a CSV file.",
        )

    content = await file.read(5 * 1024 * 1024 + 1)

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(content) > 5 * 1024 * 1024:  # 5 MB limit
        raise HTTPException(
            status_code=400,
            detail="File is too large. Maximum size is 5 MB.",
        )

    try:
        raw_transactions, parse_warnings = parse_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    categorized, cat_warnings = categorize_transactions(raw_transactions)
    summary = compute_summary(categorized)

    all_warnings = parse_warnings + cat_warnings

    return ParseResponse(
        transactions=categorized,
        summary=summary,
        warnings=all_warnings,
    )


@app.post("/api/transactions/recalculate", response_model=FinancialSummary)
async def recalculate_summary(request: RecalculateRequest):
    """
    Recalculate the financial summary after the user has edited transactions.
    """
    return compute_summary(request.transactions)


@app.post("/api/transactions/correct", response_model=ParseResponse)
async def correct_transaction(request: TransactionCorrectionRequest):
    """
    Dedicated endpoint to apply a manual correction to a transaction and return
    the updated transaction list with freshly recalculated summaries.
    """
    found = False
    updated_transactions = []

    for tx in request.transactions:
        if tx.id == request.transaction_id:
            found = True
            updated_tx = tx.model_copy(
                update={
                    "transaction_type": request.update.transaction_type,
                    "business_category": request.update.business_category,
                    "review_status": ReviewStatus.USER_CORRECTED,
                    "explanation": f"Manually corrected to '{request.update.business_category.value}' ({request.update.transaction_type.value}).",
                }
            )
            invalid_direction = (
                updated_tx.transaction_type.value in ("income", "refund") and updated_tx.amount <= 0
            ) or (
                updated_tx.transaction_type.value in ("expense", "fee") and updated_tx.amount >= 0
            )
            if (updated_tx.transaction_type.value == "unknown"
                    or updated_tx.business_category.value == "Unknown" or invalid_direction):
                updated_tx.review_status = ReviewStatus.NEEDS_REVIEW
            updated_transactions.append(updated_tx)
        else:
            updated_transactions.append(tx)

    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction #{request.transaction_id} not found in the provided list.",
        )

    new_summary = compute_summary(updated_transactions)

    return ParseResponse(
        transactions=updated_transactions,
        summary=new_summary,
        warnings=[],
    )


@app.get("/api/demo", response_model=ParseResponse)
def demo_data():
    """
    Return pre-categorized sample data for testing/demo purposes.
    Guaranteed to work even if local disk files are missing.
    """
    candidate_paths = [
        Path(__file__).resolve().parent.parent / "data" / "sample_statement.csv",
        Path.cwd() / "data" / "sample_statement.csv",
    ]

    csv_text = None
    for p in candidate_paths:
        if p.exists():
            try:
                csv_text = p.read_text(encoding="utf-8-sig")
                break
            except Exception:
                pass

    if csv_text is None:
        csv_text = EMBEDDED_SAMPLE_CSV

    try:
        raw_transactions, parse_warnings = parse_csv(csv_text)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Error parsing sample data: {e}")

    categorized, cat_warnings = categorize_transactions(raw_transactions)
    summary = compute_summary(categorized)

    return ParseResponse(
        transactions=categorized,
        summary=summary,
        warnings=parse_warnings + cat_warnings,
    )
