from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.categorizer import CATEGORIES
from app.csv_parser import StatementFormatError, parse_statement

app = FastAPI(
    title="Statement Categorizer",
    description="Categorize CSV bank statement transactions with explicit Python rules.",
    version="1.0.0",
)


class Transaction(BaseModel):
    row_number: int
    date: str
    description: str
    amount: float
    category: str
    transaction_type: Literal["purchase", "income", "refund", "transfer", "unknown"]
    needs_review: bool
    review_reason: str | None


class InvalidRow(BaseModel):
    row_number: int
    errors: list[str]
    row_data: dict[str, object]


class CategorizeResponse(BaseModel):
    transactions: list[Transaction]
    invalid_rows: list[InvalidRow]
    category_totals: dict[str, float]
    total_rows: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/categorize", response_model=CategorizeResponse)
async def categorize_statement(file: UploadFile = File(...)) -> CategorizeResponse:
    content = await file.read()
    try:
        result = parse_statement(content)
    except StatementFormatError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        await file.close()

    return CategorizeResponse(
        transactions=result.transactions,
        invalid_rows=result.invalid_rows,
        category_totals=result.category_totals,
        total_rows=result.total_rows,
    )


@app.get("/categories")
def get_categories() -> dict[str, tuple[str, ...]]:
    return {"categories": CATEGORIES}
