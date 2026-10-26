import csv
import io
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from . import database
from .csv_parser import MAX_FILE_BYTES, CSVValidationError, parse_csv
from .models import (
    EXPENSE_CATEGORIES,
    Category,
    CategoryUpdate,
    Statement,
    StatementDetail,
    Summary,
    Transaction,
)
from .summary import summarize

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    database.initialize_database(application.state.db_path)
    yield


app = FastAPI(title="Statement Categorizer", lifespan=lifespan)
app.state.db_path = Path(
    os.environ.get(
        "DATABASE_PATH",
        Path(__file__).resolve().parents[1] / "data" / "statements_pkr.sqlite3",
    )
)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    messages = [
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=422, content={"detail": "Invalid request. " + "; ".join(messages)}
    )


@app.exception_handler(sqlite3.Error)
async def database_error(request: Request, error: sqlite3.Error):
    logger.exception("Database operation failed", exc_info=error)
    return JSONResponse(
        status_code=503,
        content={"detail": "The local database is unavailable. Please try again."},
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception):
    logger.exception("Unexpected request failure", exc_info=error)
    return JSONResponse(
        status_code=500, content={"detail": "Something went wrong. Please try again."}
    )


def require_statement(statement_id: int) -> Statement:
    statement = database.get_statement(app.state.db_path, statement_id)
    if not statement:
        raise HTTPException(404, "Statement not found.")
    return statement


def statement_detail(statement_id: int) -> StatementDetail:
    statement = require_statement(statement_id)
    transactions = database.get_transactions(app.state.db_path, statement_id)
    return StatementDetail(
        statement=statement, transactions=transactions, summary=summarize(transactions)
    )


@app.get("/api/categories", response_model=list[Category])
def categories():
    return list(Category)


@app.get("/api/statements", response_model=list[Statement])
def statements():
    return database.list_statements(app.state.db_path)


@app.post("/api/statements", response_model=StatementDetail, status_code=201)
async def upload_statement(
    request: Request, filename: str = Query(min_length=1, max_length=200)
):
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            415, "Choose a .csv file. PDF and spreadsheet files are not supported."
        )
    if (
        any(ord(character) < 32 for character in filename)
        or "/" in filename
        or "\\" in filename
    ):
        raise HTTPException(422, "Use a filename without paths or control characters.")
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_FILE_BYTES:
            raise HTTPException(413, "CSV files must be 1 MiB or smaller.")
        content.extend(chunk)
    try:
        rows = parse_csv(bytes(content))
    except CSVValidationError as error:
        raise HTTPException(422, str(error)) from None
    statement_id = await run_in_threadpool(
        database.import_statement, app.state.db_path, filename, rows
    )
    return await run_in_threadpool(statement_detail, statement_id)


@app.get("/api/statements/{statement_id}", response_model=StatementDetail)
def detail(statement_id: int):
    return statement_detail(statement_id)


@app.get(
    "/api/statements/{statement_id}/transactions", response_model=list[Transaction]
)
def transactions(statement_id: int):
    require_statement(statement_id)
    return database.get_transactions(app.state.db_path, statement_id)


@app.patch(
    "/api/statements/{statement_id}/transactions/{transaction_id}",
    response_model=StatementDetail,
)
def correct_category(statement_id: int, transaction_id: int, update: CategoryUpdate):
    require_statement(statement_id)
    rows = database.get_transactions(app.state.db_path, statement_id)
    transaction = next((row for row in rows if row.id == transaction_id), None)
    if not transaction:
        raise HTTPException(404, "Transaction not found in this statement.")
    amount = Decimal(transaction.amount)
    if update.category in EXPENSE_CATEGORIES and amount >= 0:
        raise HTTPException(
            422, "Expense categories require an outgoing (negative) amount."
        )
    if update.category in (Category.INCOME, Category.REFUND) and amount <= 0:
        raise HTTPException(
            422, "Client income and refunds require an incoming (positive) amount."
        )
    if amount == 0 and update.category != Category.REVIEW:
        raise HTTPException(
            422, "Zero amounts must remain Needs Review. Check the original statement."
        )
    database.update_category(
        app.state.db_path, statement_id, transaction_id, update.category
    )
    return statement_detail(statement_id)


@app.get("/api/statements/{statement_id}/summary", response_model=Summary)
def summary(statement_id: int):
    require_statement(statement_id)
    return summarize(database.get_transactions(app.state.db_path, statement_id))


@app.post(
    "/api/statements/{statement_id}/transactions/{transaction_id}/confirm-duplicate",
    response_model=StatementDetail,
)
def confirm_duplicate(statement_id: int, transaction_id: int):
    require_statement(statement_id)
    rows = database.get_transactions(app.state.db_path, statement_id)
    transaction = next((row for row in rows if row.id == transaction_id), None)
    if not transaction:
        raise HTTPException(404, "Transaction not found in this statement.")
    if not transaction.possible_duplicate:
        raise HTTPException(
            422, "This transaction is not flagged as a possible duplicate."
        )
    database.confirm_duplicate(app.state.db_path, statement_id, transaction_id)
    return statement_detail(statement_id)


def safe_csv_text(value: str) -> str:
    # spreadsheets may treat text starting with these characters as formulas
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


@app.get("/api/statements/{statement_id}/export")
def export(statement_id: int):
    require_statement(statement_id)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Date",
            "Description",
            "Amount",
            "Currency",
            "Type",
            "Category",
            "Review status",
            "Manually corrected",
            "Possible duplicate",
            "Duplicate confirmed",
            "Explanation",
            "Automatic category",
            "Automatic explanation",
        ]
    )
    for transaction in database.get_transactions(app.state.db_path, statement_id):
        writer.writerow(
            [
                transaction.date,
                safe_csv_text(transaction.description),
                transaction.amount,
                "PKR",
                safe_csv_text(transaction.transaction_type),
                transaction.category,
                "Needs Review"
                if transaction.needs_review
                else "Reviewed"
                if transaction.manually_corrected
                else "Categorized",
                transaction.manually_corrected,
                transaction.possible_duplicate,
                transaction.duplicate_confirmed,
                transaction.explanation,
                transaction.automatic_category,
                transaction.automatic_explanation,
            ]
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="statement-{statement_id}-categorized.csv"'
        },
    )
