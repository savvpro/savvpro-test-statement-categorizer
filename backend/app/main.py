import csv
import io
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_TRANSACTIONS = 5_000

RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Transfer", ("transfer to", "transfer from", "savings transfer", "card payment", "payment to card", "zelle", "venmo transfer", "cash app transfer", "paypal transfer")),
    ("Refund", ("refund", "returned", "purchase reversal", "credit adjustment")),
    ("Income", ("client payment", "client invoice", "freelance payout", "consulting income", "stripe payout", "square payout", "upwork payment", "invoice paid")),
    ("Meals", ("starbucks", "dunkin", "doordash", "uber eats", "grubhub", "sweetgreen", "chipotle")),
    ("Software", ("adobe", "figma", "github", "notion", "microsoft 365", "google workspace", "dropbox", "zoom", "slack", "aws", "digitalocean", "quickbooks")),
    ("Travel", ("uber trip", "lyft", "airlines", "airline", "delta air", "united airlines", "american airlines", "airbnb", "amtrak", "parking", "toll")),
    ("Office supplies", ("staples", "office depot", "office max", "fedex office", "ups store")),
    ("Advertising", ("google ads", "meta ads", "facebook ads", "linkedin ads", "mailchimp", "constant contact")),
    ("Professional services", ("legalzoom", "upwork", "fiverr", "wework")),
    ("Utilities", ("comcast business", "verizon", "at t wireless", "t mobile", "electric utility", "water utility")),
    ("Bank fees", ("bank fee", "service charge", "wire fee", "overdraft fee", "monthly account fee")),
)

HEADER_ALIASES = {
    "date": ("date", "transaction date", "posted date", "post date"),
    "description": ("description", "merchant", "details", "transaction", "payee", "name"),
    "amount": ("amount", "transaction amount"),
    "debit": ("debit", "withdrawal", "money out"),
    "credit": ("credit", "deposit", "money in"),
    "type": ("type", "transaction type", "debit credit", "dr cr"),
}


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def parse_money(value: str) -> Decimal:
    raw = value.strip()
    if not raw:
        return Decimal("0")

    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("() ")
    suffix = re.search(r"(?i)\s*(cr|dr)\s*$", raw)
    if suffix and suffix.group(1).casefold() == "dr":
        negative = True
    raw = re.sub(r"(?i)\s*(cr|dr)\s*$", "", raw)
    cleaned = re.sub(r"[^0-9.+-]", "", raw.replace(",", ""))
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Amount must be a valid number.") from exc
    return -abs(amount) if negative else amount


def transaction_amount(
    row: dict[str, Any], columns: dict[str, str], line_number: int
) -> Decimal:
    if "debit" in columns and "credit" in columns:
        debit = parse_money(str(row.get(columns["debit"]) or ""))
        credit = parse_money(str(row.get(columns["credit"]) or ""))
        if debit and credit:
            raise ValueError(f"Line {line_number}: enter either a debit or a credit, not both.")
        return -abs(debit) if debit else abs(credit)

    amount = parse_money(str(row.get(columns["amount"]) or ""))
    transaction_type = normalize_text(str(row.get(columns.get("type", ""), "") or ""))
    if transaction_type in {"debit", "withdrawal", "purchase", "expense", "dr"}:
        return -abs(amount)
    if transaction_type in {"credit", "deposit", "refund", "income", "cr"}:
        return abs(amount)
    return amount


def categorize(description: str) -> tuple[str, str, float, str]:
    normalized = normalize_text(description)
    for category, phrases in RULES:
        if any(normalize_text(phrase) in normalized for phrase in phrases):
            return category, "categorized", 0.96, f"Matched a known {category.lower()} merchant or transaction phrase."

    return (
        "Needs review",
        "review",
        0.0,
        "No specific rule matched. Confirm the merchant and business purpose before assigning a category.",
    )


def read_transactions(content: bytes) -> list[dict[str, Any]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise ValueError("The CSV must use UTF-8 or Windows-1252 text encoding.") from exc

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("The CSV must include a header row.")

    normalized_headers = {
        normalize_text(header): header for header in reader.fieldnames if header
    }
    columns: dict[str, str] = {}
    for field, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized_headers:
                columns[field] = normalized_headers[alias]
                break

    if "date" not in columns or "description" not in columns:
        raise ValueError("Include date and description (or merchant) columns.")
    if "amount" not in columns and not {"debit", "credit"} <= columns.keys():
        raise ValueError("Include an amount column, or both debit and credit columns.")

    transactions = []
    for row in reader:
        line_number = reader.line_num
        if not any(str(value or "").strip() for value in row.values()):
            continue
        if None in row:
            raise ValueError(f"Line {line_number}: the row has more values than the header.")
        date = str(row.get(columns["date"]) or "").strip()
        description = str(row.get(columns["description"]) or "").strip()
        if not date or not description:
            raise ValueError(f"Line {line_number}: date and description cannot be blank.")
        try:
            amount = transaction_amount(row, columns, line_number)
        except ValueError as exc:
            message = str(exc)
            if not message.startswith("Line "):
                message = f"Line {line_number}: {message}"
            raise ValueError(message) from exc

        category, status, confidence, reason = categorize(description)
        transactions.append(
            {
                "id": str(len(transactions) + 1),
                "date": date,
                "description": description,
                "amount": float(amount.quantize(Decimal("0.01"))),
                "category": category,
                "status": status,
                "confidence": confidence,
                "reason": reason,
            }
        )
        if len(transactions) > MAX_TRANSACTIONS:
            raise ValueError(f"A statement can contain at most {MAX_TRANSACTIONS:,} transactions.")

    if not transactions:
        raise ValueError("No transactions were found in the CSV.")
    return transactions


app = FastAPI(title="Freelance Ledger API", version="1.0.0")
origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/categorize")
async def categorize_statement(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload a CSV statement.")

    content = bytearray()
    while chunk := await file.read(64 * 1024):
        content.extend(chunk)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="The CSV must be 5 MB or smaller.")

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded CSV is empty.")
    try:
        transactions = read_transactions(bytes(content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"transactions": transactions, "filename": file.filename}
