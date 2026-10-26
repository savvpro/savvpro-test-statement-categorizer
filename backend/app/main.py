import uuid
from collections import defaultdict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import rules as R
from .brain import Brain, kind_for
from .parsing import ParseError, parse_statement

MAX_BYTES = 1_000_000

app = FastAPI(title="Statement Categorizer")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

brain = Brain()
STATEMENTS: dict[str, dict] = {}  # in-memory; swap for a DB in production


class Correction(BaseModel):
    category: str
    remember: bool = True


def _summary(txns: list[dict]) -> dict:
    totals: dict[str, float] = defaultdict(float)
    income = excluded = 0.0
    for t in txns:
        if t["kind"] == "income":
            income += t["amount"]
        elif t["kind"] == "transfer":
            excluded += abs(t["amount"])
        else:  # spend adds, refunds subtract
            totals[t["category"]] += -t["amount"]
    return {
        "category_totals": {k: round(v, 2) for k, v in sorted(totals.items())},
        "income_total": round(income, 2),
        "excluded_total": round(excluded, 2),
        "needs_review_count": sum(t["needs_review"] for t in txns),
    }


def _view(sid: str) -> dict:
    s = STATEMENTS[sid]
    return {**s, "summary": _summary(s["transactions"])}


@app.get("/categories")
def categories() -> list[str]:
    return R.CATEGORIES


@app.post("/statements")
async def upload(file: UploadFile = File(...)) -> dict:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Only .csv files are supported")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 1 MB)")
    try:
        rows, warnings = parse_statement(data.decode("utf-8", errors="replace"))
    except ParseError as e:
        raise HTTPException(422, str(e))

    txns, seen = [], {}
    for i, r in enumerate(rows):
        res = brain.classify(r.description, r.amount)
        t = {"id": i, "date": r.date, "description": r.description, "amount": r.amount,
             "normalized": res.norm, "kind": res.kind, "category": res.category,
             "confidence": round(res.confidence, 2), "needs_review": res.needs_review, "reason": res.reason}
        key = (r.date, res.norm, r.amount)
        if key in seen:  # identical rows might be a double-posting: let the user decide
            t["needs_review"] = True
            t["reason"] = f"Possible duplicate of row {seen[key]}. {t['reason']}"
        else:
            seen[key] = i
        txns.append(t)

    sid = uuid.uuid4().hex[:12]
    STATEMENTS[sid] = {"id": sid, "filename": file.filename, "transactions": txns, "warnings": warnings}
    return _view(sid)


@app.get("/statements/{sid}")
def get_statement(sid: str) -> dict:
    if sid not in STATEMENTS:
        raise HTTPException(404, "Statement not found")
    return _view(sid)


@app.patch("/statements/{sid}/transactions/{tid}")
def correct(sid: str, tid: int, body: Correction) -> dict:
    if sid not in STATEMENTS:
        raise HTTPException(404, "Statement not found")
    if body.category not in R.CATEGORIES or body.category == R.REVIEW:
        raise HTTPException(422, "Unknown category")
    txns = STATEMENTS[sid]["transactions"]
    if not 0 <= tid < len(txns):
        raise HTTPException(404, "Transaction not found")

    def apply(t: dict, reason: str) -> None:
        t.update(category=body.category, kind=kind_for(body.category, t["amount"]), confidence=1.0,
                 needs_review=False, reason=reason)

    apply(txns[tid], "Set by you")
    if body.remember:
        brain.learn(txns[tid]["normalized"], body.category)
        for t in txns:
            if t["needs_review"] and t["normalized"] == txns[tid]["normalized"]:
                apply(t, "Set from a rule you saved")
    return _view(sid)
