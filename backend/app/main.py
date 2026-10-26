"""
FastAPI Application Entry Point for Freelance Ledger — Statement Categorizer.
Provides RESTful endpoints for statement preview, demo loading, summary recalculation,
and reviewed CSV export.
"""

import csv
import io
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .models import (
    CANONICAL_CATEGORIES,
    BatchRecalculateRequest,
    HealthResponse,
    StatementPreviewResponse,
    SummaryResponse,
)
from .parsing import parse_csv_statement
from .summaries import calculate_summary

app = FastAPI(
    title="Freelance Ledger — Statement Categorizer API",
    description="Deterministic rules-based financial statement categorizer for independent designers and freelancers.",
    version="1.0.0",
)

# Configure CORS for local development
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def get_health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        app="Freelance Ledger — Statement Categorizer",
        version="1.0.0",
    )


@app.get("/api/categories")
def get_categories():
    """Returns the list of canonical Schedule C categories with explanations."""
    return {
        "categories": CANONICAL_CATEGORIES,
        "descriptions": {
            "Software": "Design, engineering, and productivity SaaS subscriptions (e.g. Adobe, Figma, GitHub)",
            "Travel & Transport": "Business travel, flights, transit, and rideshares (Uber, Lyft, Amtrak)",
            "Meals & Coffee": "Business dining & coffee (Subject to 50% IRS deduction rule on Schedule C)",
            "Office Supplies & Equipment": "Stationery, computer peripherals, hardware, and equipment",
            "Internet & Utilities": "Studio internet, broadband, phone, and utility bills",
            "Advertising & Marketing": "Client acquisition ads (Google Ads, Meta/Instagram Ads)",
            "Professional Services": "Legal advisory, accounting, bookkeeping, and tax preparation",
            "Bank Fees": "Bank account maintenance charges, wire transfer fees, overdraft fees",
            "Income": "Gross revenue received from client invoices and retainers",
            "Refund": "Returned items or vendor credits (reduces expenses; not taxable income)",
            "Transfer (not spending)": "Internal money movement or card bill payment (excluded from spend/income)",
            "Personal / Owner Draw": "Personal charges on business account (non-deductible)",
            "Needs Review": "Ambiguous, generic, or low-confidence transactions requiring user confirmation",
        },
    }


@app.post("/api/statements/preview", response_model=StatementPreviewResponse)
async def preview_statement(file: Annotated[UploadFile, File()]):
    """
    Accepts CSV file upload, normalizes rows, runs deterministic categorization,
    detects potential duplicates, and returns structured transactions and financial summary.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a valid CSV file (.csv).",
        )

    # 10 MB upload size limit check
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 10 MB limit.",
        )

    if len(content.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded CSV file is empty.",
        )

    try:
        transactions, issues, total_rows = parse_csv_statement(content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while parsing the statement: {e!s}",
        )

    summary = calculate_summary(transactions)

    return StatementPreviewResponse(
        filename=file.filename,
        total_rows=total_rows,
        valid_rows=len(transactions),
        rejected_rows=len(issues),
        issues=issues,
        transactions=transactions,
        summary=summary,
    )


@app.post("/api/statements/demo", response_model=StatementPreviewResponse)
def load_demo_statement():
    """
    Loads the bundled synthetic freelancer demo statement without requiring file upload.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    demo_path = repo_root / "sample_data" / "demo_freelancer_statement.csv"

    if not demo_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo statement file not found in sample_data directory.",
        )

    with open(demo_path, "rb") as f:
        content = f.read()

    transactions, issues, total_rows = parse_csv_statement(content)
    summary = calculate_summary(transactions)

    return StatementPreviewResponse(
        filename="demo_freelancer_statement.csv",
        total_rows=total_rows,
        valid_rows=len(transactions),
        rejected_rows=len(issues),
        issues=issues,
        transactions=transactions,
        summary=summary,
    )


@app.post("/api/summary", response_model=SummaryResponse)
def recalculate_summary_endpoint(payload: BatchRecalculateRequest):
    """
    Recalculates totals and category breakdowns for edited transactions.
    """
    return calculate_summary(payload.transactions)


@app.post("/api/export")
def export_transactions_csv(payload: BatchRecalculateRequest):
    """
    Exports reviewed transactions with user modifications to a downloadable CSV.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Standard export headers
    writer.writerow([
        "Transaction ID",
        "Date",
        "Description",
        "Amount",
        "Direction",
        "Category",
        "Confidence Score",
        "Decision Reason",
        "Needs Review",
        "User Edited",
        "Duplicate Flag",
        "User Notes",
    ])

    for tx in payload.transactions:
        writer.writerow([
            tx.id,
            tx.date,
            tx.description,
            str(tx.amount),
            tx.direction,
            tx.category,
            f"{tx.confidence:.2f}",
            tx.reason,
            "YES" if tx.needs_review else "NO",
            "YES" if tx.user_edited else "NO",
            tx.duplicate_reason if tx.is_duplicate else "NO",
            tx.notes or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=freelance-ledger-reviewed-transactions.csv"
        },
    )
