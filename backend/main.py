import csv
import io
import os
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from categorizer import CATEGORIES, categorize_transaction, parse_amount

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20000

DESCRIPTION_COLUMNS = ["description", "transaction", "merchant", "details", "memo", "payee"]
AMOUNT_COLUMNS = ["amount", "transaction amount"]
DATE_COLUMNS = ["date", "transaction date", "posted date", "post date"]
DEBIT_COLUMNS = ["debit", "withdrawal", "withdrawals", "money out"]
CREDIT_COLUMNS = ["credit", "deposit", "deposits", "money in"]

# Comma separated list of allowed origins, e.g. "http://localhost:5173,https://app.example.com"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

app = FastAPI(title="Statement Categorizer API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


class CategoryUpdate(BaseModel):
    category: str


def _find(columns, names):
    return next((columns[n] for n in names if n in columns), None)


def _cell_amount(row, column):
    raw = (row.get(column) or "").strip() if column else ""
    return parse_amount(raw) if raw else 0.0


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def categories():
    return {"categories": CATEGORIES}


@app.post("/api/categorize")
async def categorize_statement(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File must be smaller than 5 MB.")

    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV header is missing.")

        columns = {name.strip().lower(): name for name in reader.fieldnames if name}
        description_col = _find(columns, DESCRIPTION_COLUMNS)
        amount_col = _find(columns, AMOUNT_COLUMNS)
        debit_col = _find(columns, DEBIT_COLUMNS)
        credit_col = _find(columns, CREDIT_COLUMNS)
        date_col = _find(columns, DATE_COLUMNS)

        if not description_col or not (amount_col or debit_col or credit_col):
            raise ValueError(
                "CSV must contain a description column and either an amount column "
                "or debit/credit columns."
            )

        transactions = []
        for row_number, row in enumerate(reader, start=2):
            if len(transactions) >= MAX_ROWS:
                raise ValueError(f"Too many rows (limit {MAX_ROWS}).")

            description = (row.get(description_col) or "").strip()
            if amount_col:
                raw_amounts = [(row.get(amount_col) or "").strip()]
            else:
                raw_amounts = [(row.get(debit_col) or "").strip() if debit_col else "",
                               (row.get(credit_col) or "").strip() if credit_col else ""]

            if not description and not any(raw_amounts):
                continue  # blank line
            if not any(raw_amounts):
                raise ValueError(f"Missing amount on CSV row {row_number}.")

            try:
                if amount_col:
                    amount = parse_amount(raw_amounts[0])
                else:
                    # Debit = money out (positive), credit = money back (negative).
                    amount = round(_cell_amount(row, debit_col) - _cell_amount(row, credit_col), 2)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid amount on CSV row {row_number}.")

            result = categorize_transaction(description, amount)
            transactions.append({
                "id": str(uuid.uuid4()),
                "row": row_number,
                "date": (row.get(date_col) or "").strip() if date_col else "",
                "description": description,
                "amount": amount,
                **result,
                "original_category": result["category"],
                "manually_reviewed": False,
            })

        if not transactions:
            raise ValueError("No transactions found in the CSV.")

        return {"transactions": transactions, "count": len(transactions)}

    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        if isinstance(exc, UnicodeDecodeError):
            detail = "File must be a UTF-8 encoded CSV."
        else:
            detail = str(exc)
        raise HTTPException(status_code=400, detail=detail)


@app.patch("/api/transactions/{transaction_id}")
def update_transaction(transaction_id: str, update: CategoryUpdate):
    """Validate a manual category edit.

    The API is intentionally stateless (no database), so the client keeps the
    edited rows. This endpoint guarantees only valid categories are accepted.
    """
    if update.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category.")
    return {"id": transaction_id, "category": update.category}
