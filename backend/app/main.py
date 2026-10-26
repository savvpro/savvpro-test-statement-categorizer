import csv
import io
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.categorizer import TAX_CATEGORIES, categorize_transaction, parse_amount

app = FastAPI(
    title="Statement Categorizer API",
    description="Deterministic rule-based statement categorizer for freelance tax preparation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

DATE_ALIASES = ["date", "transaction date", "trans date", "posting date", "posted date", "time"]
DESC_ALIASES = ["description", "desc", "merchant", "payee", "details", "memo", "name", "narrative"]
AMOUNT_ALIASES = ["amount", "amt", "total", "net"]
DEBIT_ALIASES = ["debit", "withdrawal", "spent", "charge"]
CREDIT_ALIASES = ["credit", "deposit", "refund"]

ALL_CATEGORIES = list(TAX_CATEGORIES.keys()) + [
    "Client Revenue",
    "Transfer",
    "Personal / Non-Deductible",
    "Needs Review",
]


class TransactionRow(BaseModel):
    id: int
    date: str
    description: str
    amount: str
    category: str
    confidence: str
    reason: str
    transaction_type: str
    include_in_expenses: bool
    is_tax_deductible: bool


class RecalculateRequest(BaseModel):
    transactions: List[TransactionRow]


def find_column(headers: List[str], candidates: List[str]) -> Optional[str]:
    lookup = {h.strip().lower(): h for h in headers if h}
    for cand in candidates:
        if cand in lookup:
            return lookup[cand]
    return None


def calculate_metrics(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    gross_expenses = Decimal("0")
    total_refunds = Decimal("0")
    total_income = Decimal("0")
    needs_review_count = 0
    categorized_count = 0
    category_totals: Dict[str, Decimal] = {}
    category_counts: Dict[str, int] = {}

    for item in transactions:
        amt = parse_amount(item.get("amount", "0")) or Decimal("0")
        cat = item.get("category", "Needs Review")
        tx_type = item.get("transaction_type", "expense")

        category_counts[cat] = category_counts.get(cat, 0) + 1

        if cat == "Needs Review":
            needs_review_count += 1
        else:
            categorized_count += 1

        if tx_type == "refund":
            abs_val = abs(amt)
            total_refunds += abs_val
            category_totals[cat] = category_totals.get(cat, Decimal("0")) - abs_val
        elif cat == "Client Revenue" or tx_type == "income":
            total_income += abs(amt)
            category_totals[cat] = category_totals.get(cat, Decimal("0")) + abs(amt)
        elif item.get("include_in_expenses") or item.get("is_tax_deductible"):
            abs_val = abs(amt)
            gross_expenses += abs_val
            category_totals[cat] = category_totals.get(cat, Decimal("0")) + abs(amt)

    net_expenses = gross_expenses - total_refunds
    net_profit = total_income - net_expenses

    breakdown = [
        {
            "category": c,
            "total": f"{category_totals.get(c, Decimal('0')):.2f}",
            "count": category_counts.get(c, 0),
        }
        for c in ALL_CATEGORIES
        if category_counts.get(c, 0) > 0
    ]

    return {
        "total_transactions": len(transactions),
        "categorized_count": categorized_count,
        "needs_review_count": needs_review_count,
        "gross_expenses": f"{gross_expenses:.2f}",
        "total_refunds": f"{total_refunds:.2f}",
        "net_expenses": f"{net_expenses:.2f}",
        "total_income": f"{total_income:.2f}",
        "net_profit": f"{net_profit:.2f}",
        "category_breakdown": breakdown,
    }


def process_statement_bytes(content: bytes, filename: str) -> Dict[str, Any]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(text))
    raw_headers = reader.fieldnames or []
    if not raw_headers:
        raise HTTPException(status_code=400, detail="CSV file contains no header row.")

    date_col = find_column(raw_headers, DATE_ALIASES)
    desc_col = find_column(raw_headers, DESC_ALIASES)
    amount_col = find_column(raw_headers, AMOUNT_ALIASES)
    debit_col = find_column(raw_headers, DEBIT_ALIASES)
    credit_col = find_column(raw_headers, CREDIT_ALIASES)

    if not date_col or not desc_col or (not amount_col and not (debit_col and credit_col)):
        raise HTTPException(
            status_code=400,
            detail="CSV must contain date, description, and amount (or debit/credit) columns.",
        )

    transactions = []
    for idx, row in enumerate(reader, start=1):
        date_val = (row.get(date_col) or "").strip()
        desc_val = (row.get(desc_col) or "").strip()

        if amount_col:
            amt_str = (row.get(amount_col) or "").strip()
        else:
            d_str = (row.get(debit_col) or "").strip()
            c_str = (row.get(credit_col) or "").strip()
            d_val = parse_amount(d_str) if d_str else None
            c_val = parse_amount(c_str) if c_str else None

            if d_val is not None and d_val != 0:
                amt_str = str(-abs(d_val))
            elif c_val is not None:
                amt_str = str(abs(c_val))
            else:
                amt_str = ""

        if not date_val and not desc_val and not amt_str:
            continue

        parsed = parse_amount(amt_str)
        if not date_val or not desc_val or parsed is None:
            transactions.append({
                "id": idx,
                "date": date_val or "Unknown",
                "description": desc_val or "Missing description",
                "amount": amt_str or "0.00",
                "category": "Needs Review",
                "confidence": "low",
                "reason": "Missing or unparseable date, description, or amount.",
                "transaction_type": "unknown",
                "include_in_expenses": False,
                "is_tax_deductible": False,
            })
            continue

        res = categorize_transaction(desc_val, str(parsed))
        transactions.append({
            "id": idx,
            "date": date_val,
            "description": desc_val,
            "amount": f"{parsed:.2f}",
            **res,
        })

    if not transactions:
        raise HTTPException(status_code=400, detail="No transaction rows found in CSV.")

    metrics = calculate_metrics(transactions)
    return {
        "filename": filename,
        **metrics,
        "transactions": transactions,
    }


@app.get("/")
def home():
    return {
        "service": "Statement Categorizer API",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.get("/api/categories")
def get_categories():
    return {"categories": ALL_CATEGORIES}


@app.get("/api/sample")
def get_sample_data():
    sample_rows = [
        {"id": 1, "date": "2026-10-01", "description": "ADOBE CREATIVE CLOUD", "amount": "-29.99"},
        {"id": 2, "date": "2026-10-02", "description": "UBER TRIP *CLIENT MTG", "amount": "-18.50"},
        {"id": 3, "date": "2026-10-03", "description": "TRANSFER TO SAVINGS", "amount": "-500.00"},
        {"id": 4, "date": "2026-10-04", "description": "JOES CAFE 9921", "amount": "-12.00"},
        {"id": 5, "date": "2026-10-05", "description": "REFUND ADOBE CREATIVE CLOUD", "amount": "29.99"},
        {"id": 6, "date": "2026-10-06", "description": "CLIENT PAYMENT INV-402", "amount": "1450.00"},
        {"id": 7, "date": "2026-10-07", "description": "GITHUB CO-PILOT SUB", "amount": "-10.00"},
        {"id": 8, "date": "2026-10-08", "description": "STAPLES PRINTER PAPER", "amount": "-34.50"},
        {"id": 9, "date": "2026-10-09", "description": "GOOGLE ADS CAMPAIGN", "amount": "-120.00"},
        {"id": 10, "date": "2026-10-10", "description": "CHECKING MONTHLY SERVICE FEE", "amount": "-15.00"},
        {"id": 11, "date": "2026-10-11", "description": "SQ *UNKNOWN VENDOR 331", "amount": "-8.75"},
    ]

    categorized = []
    for row in sample_rows:
        res = categorize_transaction(row["description"], row["amount"])
        categorized.append({**row, **res})

    metrics = calculate_metrics(categorized)
    return {
        "filename": "sample_statement.csv",
        **metrics,
        "transactions": categorized,
    }


@app.post("/api/recalculate")
def recalculate(req: RecalculateRequest):
    tx_dicts = [t.model_dump() for t in req.transactions]
    metrics = calculate_metrics(tx_dicts)
    return {
        **metrics,
        "transactions": tx_dicts,
    }


@app.post("/api/categorize")
async def categorize_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a valid CSV file.")

    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 5 MB allowed.")

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")

    try:
        return process_statement_bytes(content, file.filename)
    finally:
        await file.close()
