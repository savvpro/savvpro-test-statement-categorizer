
import csv
import io
import math
from datetime import datetime

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from categorizer import categorize_transaction


app = FastAPI(
    title="E-commerce Statement Categorizer",
    description="Categorize fictional e-commerce business transactions.",
    version="1.0.0",
)

# Allow the local React development server to access this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

REQUIRED_COLUMNS = {"date", "description", "amount"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB


@app.get("/health")
def health_check():
    """Check whether the API is running."""
    return {"status": "ok"}


@app.post("/categorize")
async def categorize_statement(file: UploadFile = File(...)):
    """Upload a CSV statement and categorize its transactions."""

    # Validate the uploaded file type.
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    # Read at most 2 MB plus one byte to detect oversized files.
    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large. Maximum size is 2 MB.",
        )

    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        # Validate the CSV header.
        if not reader.fieldnames:
            raise HTTPException(
                status_code=400,
                detail="The CSV file is empty or missing headers.",
            )

        # Normalize header names and surrounding whitespace.
        reader.fieldnames = [
            name.strip().lower() if name else ""
            for name in reader.fieldnames
        ]

        # Reject duplicate column headers after normalization.
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise HTTPException(
                status_code=400,
                detail="CSV contains duplicate column headers.",
            )

        # Check that all required columns are present.
        if not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
            raise HTTPException(
                status_code=400,
                detail=(
                    "CSV must contain date, description, and amount columns."
                ),
            )

        transactions = []

        for row_number, row in enumerate(reader, start=2):
            # Ignore completely blank lines.
            if not any(
                isinstance(value, str) and value.strip()
                for value in row.values()
            ):
                continue

            # Reject rows that contain more fields than the CSV header.
            if None in row:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unexpected extra columns on CSV row {row_number}.",
                )

            date = (row.get("date") or "").strip()
            description = (row.get("description") or "").strip()
            raw_amount = (row.get("amount") or "").strip()

            # Validate that the date is present.
            if not date:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing date on CSV row {row_number}.",
                )

            # Validate the date format and ensure the date actually exists.
            try:
                parsed_date = datetime.strptime(date, "%Y-%m-%d")

                if parsed_date.strftime("%Y-%m-%d") != date:
                    raise ValueError

            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid date on CSV row {row_number}. "
                        "Use YYYY-MM-DD format."
                    ),
                )

            # Validate that the amount is present.
            if not raw_amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing amount on CSV row {row_number}.",
                )

            # Convert the amount to a number.
            try:
                amount = float(raw_amount)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid amount on CSV row {row_number}.",
                )

            # Reject NaN and infinity.
            if not math.isfinite(amount):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid amount on CSV row {row_number}.",
                )

            # Categorize the transaction using explicit Python rules.
            result = categorize_transaction(description, amount)

            transactions.append(
                {
                    "date": date,
                    "description": description,
                    "amount": amount,
                    "category": result["category"],
                    "reason": result["reason"],
                }
            )

        # Reject CSV files that contain no transactions.
        if not transactions:
            raise HTTPException(
                status_code=400,
                detail="No transactions were found in the CSV file.",
            )

        return {
            "filename": file.filename,
            "transaction_count": len(transactions),
            "transactions": transactions,
        }

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Please upload a UTF-8 encoded CSV file.",
        )
