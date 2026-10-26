from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import store
from .engine import categorize_all
from .parser import parse_csv
from .rules import CATEGORIES
from .schemas import NEEDS_REVIEW, CategoryUpdate, Summary, Transaction, UploadResponse
from .summary import summarize

MAX_UPLOAD_BYTES = 1_000_000
ASSIGNABLE = [c for c in CATEGORIES if c != NEEDS_REVIEW]

app = FastAPI(title="Statement Categorizer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile) -> UploadResponse:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, f"File too large: the limit is {MAX_UPLOAD_BYTES // 1000} KB.")
    try:
        parsed = parse_csv(data.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise HTTPException(400, "File is not valid UTF-8 text.") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    if not parsed.transactions:
        detail = "No valid rows found in the file."
        raise HTTPException(400, " ".join([detail, *parsed.errors[:3]]))
    transactions = categorize_all(parsed.transactions)
    store.replace(transactions)
    return UploadResponse(transactions=transactions, skipped_rows=parsed.errors)


@app.get("/transactions", response_model=list[Transaction])
def list_transactions(needs_review: bool | None = None, category: str | None = None):
    rows = store.all_transactions()
    if needs_review is not None:
        rows = [t for t in rows if t.needs_review == needs_review]
    if category is not None:
        rows = [t for t in rows if t.category == category]
    return rows


@app.patch("/transactions/{tx_id}", response_model=list[Transaction])
def update_category(tx_id: int, body: CategoryUpdate):
    if body.category not in ASSIGNABLE:
        raise HTTPException(400, f"Invalid category {body.category!r}. See GET /categories.")
    tx = store.get(tx_id)
    if tx is None:
        raise HTTPException(404, f"Transaction {tx_id} not found.")
    tx.category = body.category
    tx.confidence = 1.0
    tx.reason = "Edited by user"
    tx.user_edited = True
    tx.needs_review = False
    return store.all_transactions()


@app.get("/summary", response_model=Summary)
def summary() -> Summary:
    return summarize(store.all_transactions())


@app.get("/categories", response_model=list[str])
def categories() -> list[str]:
    return ASSIGNABLE
