import csv
import io
import re
import secrets
from collections import defaultdict
from dataclasses import asdict, dataclass
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="Studio Ledger Categorizer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATEGORIES = [
    "Software",
    "Travel",
    "Meals",
    "Office supplies",
    "Professional services",
    "Advertising",
    "Income",
    "Transfer",
    "Refund",
    "Needs review",
]

RULES = [
    ("Transfer", ("transfer", "tfr", "zelle", "venmo", "cash app", "payment thank")),
    ("Refund", ("refund", "credit adjustment", "return credit", "reversal")),
    ("Income", ("client payment", "invoice", "stripe payout", "paypal transfer in", "deposit")),
    ("Software", ("adobe", "figma", "notion", "dropbox", "slack", "canva", "github", "zoom", "microsoft 365")),
    ("Travel", ("uber", "lyft", "airbnb", "delta", "united airlines", "southwest", "hotel", "parking", "amtrak")),
    ("Meals", ("starbucks", "doordash", "grubhub", "sweetgreen", "meal")),
    ("Office supplies", ("staples", "office depot", "paper source", "amazon business", "b&h photo", "walmart")),
    ("Professional services", ("legal", "accounting", "bookkeeping", "consulting", "contractor")),
    ("Advertising", ("google ads", "meta ads", "facebook ads", "linkedin ads", "mailchimp")),
]


@dataclass
class Transaction:
    id: str
    date: str
    description: str
    amount: float
    category: str
    confidence: str
    reason: str


class ReviewRequest(BaseModel):
    category: str


class LoginRequest(BaseModel):
    email: str
    password: str


DEMO_USER = {"email": "demo@studioledger.com", "name": "Alex Morgan", "workspace": "Morgan Design Co."}
SESSIONS: set[str] = set()
DEMO_TRANSACTIONS = [
    Transaction("1", "2026-01-02", "ADOBE CREATIVE CLOUD", -59.99, "Software", "high", "Matched the 'adobe' merchant rule."),
    Transaction("2", "2026-01-03", "UBER *TRIP", -24.60, "Travel", "high", "Matched the 'uber' merchant rule."),
    Transaction("3", "2026-01-04", "TRANSFER TO SAVINGS", -500.00, "Transfer", "high", "Matched the 'transfer' merchant rule."),
    Transaction("4", "2026-01-06", "JOES CAFE 9921", -18.25, "Needs review", "low", "No trusted merchant rule matched this description."),
    Transaction("5", "2026-01-09", "CLIENT PAYMENT ACME", 2400.00, "Income", "high", "Matched the 'client payment' merchant rule."),
]


def require_session(token: str | None) -> None:
    if not token or token not in SESSIONS:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")


def parse_amount(value: str) -> float:
    cleaned = value.strip().replace("$", "").replace(",", "")
    if not cleaned:
        raise ValueError("amount is empty")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    return float(cleaned)


def classify(description: str, amount: float) -> tuple[str, str, str]:
    normalized = re.sub(r"\s+", " ", description.lower()).strip()
    for category, keywords in RULES:
        matched = next((keyword for keyword in keywords if keyword in normalized), None)
        if matched:
            if category == "Income" and amount < 0:
                return "Needs review", "low", "An income keyword appears on a debit; verify the transaction direction."
            return category, "high", f"Matched the {matched!r} merchant rule."
    return "Needs review", "low", "No trusted merchant rule matched this description."


def parse_statement(content: bytes) -> list[Transaction]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Upload a UTF-8 CSV file.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="The CSV needs a header row.")
    fields = {field.strip().lower(): field for field in reader.fieldnames if field}
    required = {"date", "description", "amount"}
    if not required.issubset(fields):
        raise HTTPException(status_code=400, detail="CSV headers must include Date, Description, and Amount.")
    transactions = []
    for row_number, row in enumerate(reader, start=2):
        try:
            date = row[fields["date"]].strip()
            description = row[fields["description"]].strip()
            amount = parse_amount(row[fields["amount"]])
            if not date or not description:
                raise ValueError("date and description are required")
        except (AttributeError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid transaction on CSV row {row_number}.") from exc
        category, confidence, reason = classify(description, amount)
        transactions.append(Transaction(str(row_number - 1), date, description, amount, category, confidence, reason))
    if not transactions:
        raise HTTPException(status_code=400, detail="The CSV does not contain any transactions.")
    return transactions


def build_summary(transactions: list[Transaction]) -> dict[str, float]:
    summary = defaultdict(float)
    for transaction in transactions:
        summary[transaction.category] += transaction.amount
    return {category: round(summary[category], 2) for category in CATEGORIES if category in summary}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/statements")
async def upload_statement(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv statement.")
    transactions = parse_statement(await file.read())
    return {
        "filename": file.filename,
        "transactions": [asdict(transaction) for transaction in transactions],
        "summary": build_summary(transactions),
        "categories": CATEGORIES,
    }


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict:
    if request.email.lower() != DEMO_USER["email"] or request.password != "demo123":
        raise HTTPException(status_code=401, detail="Use the demo credentials shown below.")
    token = secrets.token_urlsafe(24)
    SESSIONS.add(token)
    return {"token": token, "user": DEMO_USER}


@app.get("/api/me")
def me(token: str | None = None) -> dict:
    require_session(token)
    return DEMO_USER


@app.get("/api/dashboard")
def dashboard(token: str | None = None) -> dict:
    require_session(token)
    return {"transactions": [asdict(item) for item in DEMO_TRANSACTIONS], "summary": build_summary(DEMO_TRANSACTIONS), "categories": CATEGORIES}


@app.get("/api/rules")
def rules(token: str | None = None) -> dict:
    require_session(token)
    return {"rules": [{"category": category, "keywords": list(keywords), "description": f"Matches trusted {category.lower()} merchants."} for category, keywords in RULES]}


@app.patch("/api/transactions/{transaction_id}")
def update_transaction(transaction_id: str, request: ReviewRequest, token: str | None = None) -> dict:
    require_session(token)
    if request.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Choose a valid category.")
    return {"id": transaction_id, "category": request.category}
