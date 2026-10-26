from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.brain.categorizer import categorize_all, summarize_by_category
from app.models import (
    CategoriesResponse,
    CategorizeResponse,
    Category,
    CategorizedTransaction,
    UpdateCategoryRequest,
)
from app.parser.statement_parser import parse_statement_csv

app = FastAPI(title="Statement Categorizer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store for demo (single-user local assessment)
_session: dict[str, CategorizedTransaction] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories", response_model=CategoriesResponse)
def list_categories():
    return CategoriesResponse(categories=[c.value for c in Category])


@app.post("/api/categorize", response_model=CategorizeResponse)
async def categorize_statement(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV statement exports are supported.")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB).")

    try:
        transactions = parse_statement_csv(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    categorized = categorize_all(transactions)
    _session.clear()
    for tx in categorized:
        _session[tx.id] = tx

    summaries = summarize_by_category(categorized)
    needs_review = sum(1 for t in categorized if t.effective_category == Category.NEEDS_REVIEW)

    return CategorizeResponse(
        transactions=categorized,
        summaries=summaries,
        needs_review_count=needs_review,
    )


@app.patch("/api/transactions", response_model=CategorizeResponse)
def update_transaction(body: UpdateCategoryRequest):
    tx = _session.get(body.transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found. Upload a statement first.")

    updated = tx.model_copy(update={"user_category": body.category})
    _session[body.transaction_id] = updated

    all_tx = list(_session.values())
    return CategorizeResponse(
        transactions=all_tx,
        summaries=summarize_by_category(all_tx),
        needs_review_count=sum(1 for t in all_tx if t.effective_category == Category.NEEDS_REVIEW),
    )
