from __future__ import annotations
import csv, io, re
from collections import defaultdict
from datetime import datetime
from typing import Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Ledgerly Statement Categorizer", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173","http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

CATEGORIES = ["Software", "Office Supplies", "Travel", "Meals", "Marketing", "Professional Services", "Utilities", "Equipment", "Bank Fees", "Income", "Transfer", "Refund", "Needs Review"]
RULES = [
    (r"\b(adobe|figma|github|notion|slack|microsoft 365|dropbox|canva|zoom|aws|google workspace|openai)\b", "Software", "Known software or SaaS merchant"),
    (r"\b(staples|office depot|paper|stationery|officeworks)\b", "Office Supplies", "Office supply merchant"),
    (r"\b(uber|lyft|taxi|airbnb|hotel|airlines|delta air|united airlines|train|railway|parking|shell|chevron|bp fuel)\b", "Travel", "Travel or transport merchant"),
    (r"\b(cafe|coffee|restaurant|grill|pizza|doordash|ubereats|deliveroo|foodpanda)\b", "Meals", "Food or dining merchant"),
    (r"\b(meta ads|facebook ads|google ads|linkedin ads|mailchimp|constant contact|printful)\b", "Marketing", "Advertising or marketing service"),
    (r"\b(legal|law firm|accountant|accounting|consulting|consultant|tax prep|freelancer)\b", "Professional Services", "Professional service merchant"),
    (r"\b(electric|water utility|internet|comcast|verizon|at&t|t-mobile|gas utility)\b", "Utilities", "Utility or communications provider"),
    (r"\b(dell|apple store|best buy|hewlett.packard|lenovo|monitor|keyboard)\b", "Equipment", "Computer or equipment merchant"),
    (r"\b(bank fee|monthly service fee|overdraft fee|wire fee|atm fee)\b", "Bank Fees", "Bank fee descriptor"),
]
DATE_KEYS = ("date", "transaction date", "posted date")
DESC_KEYS = ("description", "transaction", "merchant", "details", "payee", "memo")
AMOUNT_KEYS = ("amount", "transaction amount", "value")
DEBIT_KEYS = ("debit", "withdrawal", "money out")
CREDIT_KEYS = ("credit", "deposit", "money in")

def _key(row: dict[str, Any], choices: tuple[str, ...]):
    lowered = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    for choice in choices:
        if choice in lowered and str(lowered[choice]).strip():
            return lowered[choice]
    return None

def _money(value: Any) -> float:
    if value is None: return 0.0
    s = str(value).strip().replace("$", "").replace("£", "").replace("€", "").replace(",", "").replace(" ", "")
    if not s or s in {"-", "—"}: return 0.0
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try: n = float(s)
    except ValueError: raise ValueError(f"Invalid amount: {value}")
    return -abs(n) if negative else n

def categorize(description: str, amount: float) -> tuple[str, str, float]:
    """Return category, rationale and confidence. Rules are deterministic and auditable."""
    text = re.sub(r"\s+", " ", (description or "").upper()).strip()
    if re.search(r"\b(TRANSFER TO|TRANSFER FROM|INTERNAL TRANSFER|SAVINGS TRANSFER|CARD PAYMENT|CREDIT CARD PAYMENT)\b", text):
        return "Transfer", "Transfer/payment movement; excluded from income and expense totals", 0.99
    if re.search(r"\b(REFUND|REVERSAL|RETURN CREDIT|MERCHANDISE CREDIT)\b", text) or (amount > 0 and re.search(r"\b(AMZN|AMAZON|UBER|ADOBE|WALMART|TARGET)\b", text) and "REFUND" in text):
        return "Refund", "Descriptor indicates money returned; not counted as income", 0.96
    if amount > 0:
        if re.search(r"\b(PAYROLL|CLIENT PAYMENT|INVOICE PAYMENT|STRIPE PAYOUT|PAYPAL TRANSFER|ACH CREDIT|DIRECT DEPOSIT)\b", text):
            return "Income", "Descriptor resembles business income", 0.91
        return "Needs Review", "Positive amount has no reliable income/refund signal", 0.35
    for pattern, category, rationale in RULES:
        if re.search(pattern, text, re.I):
            return category, rationale, 0.88
    return "Needs Review", "Merchant or transaction purpose is not confidently recognized", 0.2

def parse_statement(content: bytes, filename: str) -> list[dict[str, Any]]:
    if not filename.lower().endswith(".csv"):
        raise ValueError("For this version, upload a CSV statement exported from your bank. PDF parsing is not enabled.")
    try: text = content.decode("utf-8-sig")
    except UnicodeDecodeError: text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames: raise ValueError("CSV has no header row.")
    transactions = []
    for line, row in enumerate(reader, start=2):
        raw_desc = _key(row, DESC_KEYS)
        raw_date = _key(row, DATE_KEYS)
        raw_amount = _key(row, AMOUNT_KEYS)
        debit, credit = _key(row, DEBIT_KEYS), _key(row, CREDIT_KEYS)
        if not raw_desc and raw_amount is None and debit is None and credit is None:
            continue
        if not raw_desc: raise ValueError(f"Row {line}: missing transaction description.")
        try:
            if raw_amount is not None:
                amount = _money(raw_amount)
            elif debit is not None or credit is not None:
                amount = _money(credit) - abs(_money(debit))
            else:
                raise ValueError("missing amount column")
        except ValueError as e: raise ValueError(f"Row {line}: {e}")
        date = str(raw_date or "").strip()
        category, rationale, confidence = categorize(str(raw_desc), amount)
        transactions.append({"id": f"row-{line}", "date": date, "description": str(raw_desc).strip(), "amount": round(amount, 2), "category": category, "suggestedCategory": category, "rationale": rationale, "confidence": confidence, "status": "review" if category == "Needs Review" else "categorized"})
    if not transactions: raise ValueError("No transactions found in the CSV.")
    return transactions

def summarize(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    category_totals = defaultdict(float)
    income = expenses = refunds = 0.0
    for t in transactions:
        amount, cat = float(t["amount"]), t["category"]
        if cat == "Transfer": continue
        if cat == "Refund": refunds += abs(amount); continue
        if amount > 0 and cat == "Income": income += amount
        elif amount < 0: expenses += abs(amount)
        if amount < 0 and cat not in {"Needs Review", "Transfer", "Refund"}: category_totals[cat] += abs(amount)
    return {"transactionCount": len(transactions), "reviewCount": sum(t["category"] == "Needs Review" for t in transactions), "income": round(income, 2), "expenses": round(expenses, 2), "refunds": round(refunds, 2), "net": round(income - expenses + refunds, 2), "categoryTotals": {k: round(v, 2) for k,v in sorted(category_totals.items(), key=lambda x: -x[1])}}

class UpdateRequest(BaseModel):
    category: str

@app.get("/api/health")
def health(): return {"status": "ok", "service": "Ledgerly", "version": "1.0.0"}

@app.get("/api/categories")
def categories(): return {"categories": CATEGORIES}

@app.post("/api/categorize")
async def categorize_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024: raise ValueError("File exceeds the 10 MB limit.")
        transactions = parse_statement(content, file.filename or "")
        return {"transactions": transactions, "summary": summarize(transactions), "filename": file.filename}
    except ValueError as e: raise HTTPException(status_code=400, detail=str(e))
    except Exception: raise HTTPException(status_code=400, detail="Could not read this statement. Check that it is a valid CSV file.")

@app.post("/api/demo")
def demo():
    rows = [
        ("2026-10-02","ADOBE CREATIVE CLOUD",-59.99),("2026-10-03","UBER TRIP",-24.50),("2026-10-04","JOES CAFE 9921",-18.75),
        ("2026-10-05","CLIENT PAYMENT - INV 104",1850.00),("2026-10-06","TRANSFER TO SAVINGS",-300.00),("2026-10-07","AMAZON REFUND",32.49),
        ("2026-10-08","GOOGLE ADS",-120.00),("2026-10-09","MONTHLY SERVICE FEE",-12.00),("2026-10-10","ACME UNKNOWN 8842",-43.25),
        ("2026-10-11","NOTION LABS",-10.00),("2026-10-12","HOTEL CENTRAL",-145.00),("2026-10-13","PAYROLL DIRECT DEPOSIT",950.00),
    ]
    tx=[]
    for i,(date,desc,amount) in enumerate(rows,1):
        cat,why,conf=categorize(desc,amount)
        tx.append({"id":f"demo-{i}","date":date,"description":desc,"amount":amount,"category":cat,"suggestedCategory":cat,"rationale":why,"confidence":conf,"status":"review" if cat=="Needs Review" else "categorized"})
    return {"transactions":tx,"summary":summarize(tx),"filename":"freelancer_october_demo.csv"}

@app.patch("/api/transactions/{transaction_id}")
def update_transaction(transaction_id: str, request: UpdateRequest):
    if request.category not in CATEGORIES: raise HTTPException(status_code=400, detail="Unknown category.")
    return {"id": transaction_id, "category": request.category, "status": "review" if request.category == "Needs Review" else "categorized"}
