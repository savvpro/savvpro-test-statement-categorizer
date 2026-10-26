"""HTTP API. Stateless: the brain lives in categorizer.py, this file only
validates input and calls it."""
import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import rules
from .categorizer import categorize_all, summarize
from .parser import ParseError, parse_statement

MAX_BYTES = 5 * 1024 * 1024  # 5 MB is plenty for a statement

app = FastAPI(title="Statement Categorizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # the React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


def _category_options() -> list[str]:
    """Categories a user may pick when fixing a row."""
    options = list(rules.CATEGORIES.keys())
    for extra in ("Personal", "Income", rules.NOT_SPENDING_LABEL):
        if extra not in options:
            options.append(extra)
    return options


def _parse_user_rules(raw: str) -> dict[str, str]:
    """Validate the merchant -> category map sent by the browser."""
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "user_rules must be valid JSON")
    if not isinstance(data, dict):
        raise HTTPException(400, "user_rules must be an object")

    allowed = set(_category_options())
    for key, category in data.items():
        if not isinstance(key, str) or not isinstance(category, str):
            raise HTTPException(400, "user_rules must map text to text")
        if category.removeprefix("Refund: ") not in allowed:
            raise HTTPException(400, f"Unknown category: {category!r}")
    return data


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def categories():
    return {"categories": _category_options()}


@app.post("/api/categorize")
async def categorize_statement(
    file: UploadFile = File(...),
    charges_positive: bool = Form(False),
    user_rules: str = Form("{}"),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")

    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "File is too large (max 5 MB)")

    rules_map = _parse_user_rules(user_rules)

    try:
        transactions, skipped = parse_statement(content, charges_positive)
    except ParseError as e:
        raise HTTPException(400, str(e))

    rows = categorize_all(transactions, rules_map)
    return {"rows": rows, "summary": summarize(rows), "skipped": skipped}