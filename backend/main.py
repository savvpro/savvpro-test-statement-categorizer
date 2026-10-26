from decimal import Decimal
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from categorizer import parse_statement
from summary import build_summary


app = FastAPI(title="Freelancer Statement Categorizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)

# Prototype storage: cleared whenever the backend restarts.
statements = {}

EXPENSE_CATEGORIES = {
    "Software",
    "Travel",
    "Internet",
    "Office Supplies",
    "Other Business Expense",
}


class TransactionCorrection(BaseModel):
    type: Literal["expense", "income", "refund", "transfer", "unknown"]
    category: Literal[
        "Software",
        "Travel",
        "Internet",
        "Office Supplies",
        "Other Business Expense",
        "Client Income",
        "Transfer",
        "Needs Review",
    ]


def get_transactions(statement_id):
    if statement_id not in statements:
        raise HTTPException(
            status_code=404,
            detail="Statement not found. If the server restarted, upload again.",
        )
    return statements[statement_id]


def statement_response(statement_id):
    transactions = get_transactions(statement_id)

    return {
        "statement_id": statement_id,
        "transactions": transactions,
        "transaction_count": len(transactions),
        "needs_review_count": sum(
            transaction["needs_review"]
            for transaction in transactions
        ),
        "summary": build_summary(transactions),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/statements")
async def upload_statement(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".csv"):
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    max_size = 2 * 1024 * 1024

    try:
        content = await file.read(max_size + 1)
    finally:
        await file.close()

    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File must be 2 MB or smaller.",
        )

    try:
        transactions = parse_statement(content)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    statement_id = str(uuid4())
    statements[statement_id] = transactions

    return statement_response(statement_id)


@app.get("/statements/{statement_id}")
async def read_statement(statement_id: str):
    return statement_response(statement_id)


@app.patch("/statements/{statement_id}/transactions/{transaction_id}")
async def correct_transaction(
    statement_id: str,
    transaction_id: int,
    correction: TransactionCorrection,
):
    transactions = get_transactions(statement_id)

    transaction = next(
        (row for row in transactions if row["id"] == transaction_id),
        None,
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    amount = Decimal(transaction["amount"])
    kind = correction.type
    category = correction.category

    if kind in {"expense", "refund"}:
        if category not in EXPENSE_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail="Choose an expense category for expenses or refunds.",
            )

        if kind == "expense" and amount >= 0:
            raise HTTPException(
                status_code=400,
                detail="An expense must have a negative amount.",
            )

        if kind == "refund" and amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="A refund must have a positive amount.",
            )

    elif kind == "income":
        if category != "Client Income" or amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Income requires Client Income and a positive amount.",
            )

    elif kind == "transfer":
        if category != "Transfer" or amount == 0:
            raise HTTPException(
                status_code=400,
                detail="A transfer requires Transfer and a nonzero amount.",
            )

    elif kind == "unknown":
        if category != "Needs Review":
            raise HTTPException(
                status_code=400,
                detail="Unknown transactions must use Needs Review.",
            )

    transaction.update({
        "type": kind,
        "category": category,
        "needs_review": kind == "unknown",
        "reason": (
            "User marked this transaction for further review."
            if kind == "unknown"
            else "Category and transaction type confirmed by user."
        ),
    })

    return statement_response(statement_id)