from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from . import rules
from .parser import StatementError, parse_statement
from .service import build_rows, summarize

MAX_BYTES = 2 * 1024 * 1024

app = FastAPI(title="Statement Categorizer")


class Row(BaseModel):
    id: int
    amount: float
    category: str
    refund_of: Optional[str] = None


class SummaryRequest(BaseModel):
    rows: List[Row]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def categories():
    return {"categories": rules.ALL_CATEGORIES}


@app.post("/api/statements")
async def upload(file: UploadFile = File(...), charges_are_positive: bool = Form(True)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File is too large (limit 2 MB).")
    try:
        parsed = parse_statement(raw, charges_are_positive)
    except StatementError as error:
        raise HTTPException(400, str(error))
    rows = build_rows(parsed)
    return {"rows": rows, "errors": parsed.errors, "summary": summarize(rows)}


@app.post("/api/summary")
def summary(body: SummaryRequest):
    return summarize([r.model_dump() for r in body.rows])
