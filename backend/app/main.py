import os
from decimal import Decimal
from typing import Literal, get_args

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .parser import StatementError
from .service import categorize_statement, compute_totals

MAX_BYTES = 2 * 1024 * 1024
Category = Literal["Software", "Travel", "Meals", "Office", "Utilities",
                   "Income", "Refund", "Transfer", "Needs Review"]

app = FastAPI(title="Statement Categorizer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class TotalsRow(BaseModel):
    amount: Decimal
    category: Category


class TotalsRequest(BaseModel):
    rows: list[TotalsRow] = Field(max_length=10000)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def categories():
    return {"categories": list(get_args(Category))}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 2 MB)")
    try:
        return categorize_statement(content)
    except StatementError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/totals")
def totals(body: TotalsRequest):
    rows = [{"amount": str(r.amount), "category": r.category} for r in body.rows]
    return {"totals": compute_totals(rows)}
