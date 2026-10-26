import csv
import io

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.categorizer import CATEGORIES, categorize_transactions, summarize_transactions
from app.parser import StatementParseError, parse_statement

app = FastAPI(title="Statement Categorizer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TransactionBatch(BaseModel):
    transactions: list[dict[str, object]]


class CategoryUpdate(BaseModel):
    category: str


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/statements/parse")
async def parse_uploaded_statement(file: UploadFile = File(...)) -> dict[str, list[dict[str, str | int]]]:
    if file.content_type not in {"text/csv", "application/csv", "text/plain"}:
        raise HTTPException(status_code=415, detail="Upload a CSV statement.")

    try:
        transactions = parse_statement(await file.read())
    except StatementParseError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"transactions": transactions}


@app.post("/transactions/categorize")
def categorize_uploaded_transactions(batch: TransactionBatch) -> dict[str, list[dict[str, object]]]:
    return {"transactions": categorize_transactions(batch.transactions)}


@app.put("/transactions/{source_row}/category")
def update_transaction_category(source_row: int, update: CategoryUpdate) -> dict[str, object]:
    if update.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Choose a valid transaction category.")
    return {
        "source_row": source_row,
        "category": update.category,
        "confidence": "user",
        "reason": "Category selected by the user.",
        "needs_review": False,
    }


@app.post("/transactions/export")
def export_transactions(batch: TransactionBatch) -> dict[str, str]:
    if not batch.transactions:
        raise HTTPException(status_code=400, detail="There are no transactions to export.")

    fields = ("source_row", "date", "description", "amount", "category", "confidence", "reason", "needs_review")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(batch.transactions)
    return {"filename": "categorized-statement.csv", "csv": output.getvalue()}


@app.post("/statements/categorize")
async def categorize_uploaded_statement(file: UploadFile = File(...)) -> dict[str, object]:
    if file.content_type not in {"text/csv", "application/csv", "text/plain"}:
        raise HTTPException(status_code=415, detail="Upload a CSV statement.")

    try:
        parsed_transactions = parse_statement(await file.read())
    except StatementParseError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    transactions = categorize_transactions(parsed_transactions)
    return {"transactions": transactions, "summary": summarize_transactions(transactions)}
