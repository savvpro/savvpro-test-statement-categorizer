"""
FastAPI Statement Categorizer Service.

Provides REST endpoints for statement CSV upload, validation, deterministic categorization,
and manual category corrections with automatic summary recalculation.
"""

from typing import Any, Dict
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .models import (
    Category,
    StatementSummary,
    Transaction,
    TransactionUpdateRequest,
    UploadResponse,
)
from .parser import CSVValidationError, parse_csv_content
from .store import store

app = FastAPI(
    title="Statement Categorizer API",
    description="Deterministic transaction categorizer for freelancer tax-prep review.",
    version="1.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SAMPLE_CSV_CONTENT = """Date,Description,Amount
2026-03-01,STRIPE PAYOUT CLIENT INVOICE 1042,3200.00
2026-03-02,ADOBE CREATIVE CLOUD,-54.99
2026-03-03,UBER *TRIP TO CLIENT OFFICE,-28.45
2026-03-04,STARBUCKS #1042 SEATTLE,-7.25
2026-03-05,TRANSFER TO SAVINGS,-1000.00
2026-03-06,AMAZON WEB SERVICES AWS.AMAZON.COM,-142.10
2026-03-07,STAPLES #0822 PRINTER INK & PAPER,-89.60
2026-03-08,USPS POSTAGE TRACKING,-14.20
2026-03-09,REFUND FROM AMAZON WEB SERVICES,35.00
2026-03-10,UPWORK ESCROW MILESTONE 2,1450.00
2026-03-11,AMAZON.COM*8B3120 RETAIL,-65.40
2026-03-12,ZOOM.US MONTHLY PRO,-15.99
2026-03-13,DELTA AIRLINES FLIGHT 412,-389.00
2026-03-14,CHIPOTLE ONLINE ORDER,-14.50
2026-03-15,JOES HARDWARE 9921,-45.00
2026-03-16,GITHUB SUBSCRIPTION,-21.00
2026-03-17,WIRE TRANSFER TO CHECKING,500.00
2026-03-18,UNKNOWN VENDOR 0942,-78.00
"""

SAMPLE_CREDIT_CARD_CSV = """Date,Description,Debit,Credit
2026-03-01,ADOBE CREATIVE CLOUD,54.99,
2026-03-02,UBER TRIP AIRPORT,34.20,
2026-03-03,REFUND FROM AIRLINE,,120.00
2026-03-04,BEST BUY MONITOR MOUNT,84.99,
2026-03-05,TRANSFER TO SAVINGS,500.00,
2026-03-06,PAYPAL DEPOSIT CONSULTING,,2400.00
2026-03-07,LOCAL DINER LUNCH,18.50,
2026-03-08,CORNER BISTRO 22,25.00,
"""


@app.get("/health", tags=["System"])
def health_check() -> Dict[str, str]:
    """Health check endpoint to verify backend service readiness."""
    return {"status": "ok", "app": "Statement Categorizer API", "version": "1.0.0"}


@app.get("/api/statements/sample", response_class=PlainTextResponse, tags=["Statements"])
def get_sample_csv(format_type: str = "standard") -> str:
    """Returns sample CSV content for freelancers to test statements."""
    if format_type.lower() == "credit_card":
        return SAMPLE_CREDIT_CARD_CSV
    return SAMPLE_CSV_CONTENT


@app.post("/api/statements/upload", response_model=UploadResponse, tags=["Statements"])
async def upload_statement(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a CSV statement, validate schema and values, and deterministically categorize transactions.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a .csv file.",
        )

    try:
        content = await file.read()
        transactions, warnings = parse_csv_content(content)
        response = store.set_statement(file.filename, transactions, warnings)
        return response
    except CSVValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the file: {str(exc)}",
        )


@app.get("/api/statements/current", response_model=UploadResponse, tags=["Statements"])
def get_current_statement() -> UploadResponse:
    """Retrieve the current statement, transactions, and recalculated summary."""
    if not store.statement_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No statement has been uploaded yet.",
        )
    tx_list = store.get_all_transactions()
    summary = store.calculate_summary(tx_list)
    return UploadResponse(
        statement_id=store.statement_id,
        filename=store.filename or "statement.csv",
        transactions=tx_list,
        summary=summary,
        warnings=store.warnings,
    )


@app.patch("/api/transactions/{transaction_id}", tags=["Transactions"])
def update_transaction(transaction_id: str, payload: TransactionUpdateRequest) -> Dict[str, Any]:
    """
    Update the category of a transaction.
    Recalculates and returns the updated transaction alongside the updated summary.
    """
    try:
        updated_tx = store.update_category(transaction_id, payload.category)
        updated_summary = store.calculate_summary()
        return {
            "transaction": updated_tx,
            "summary": updated_summary,
            "message": f"Transaction category updated to '{payload.category.value}'.",
        }
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' was not found.",
        )
