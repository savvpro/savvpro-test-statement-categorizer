"""HTTP endpoints: upload, review, fix and export statements."""

from __future__ import annotations

import csv
import io
from decimal import Decimal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.brain.engine import learned_key
from app.domain.categories import CATEGORIES, NEEDS_REVIEW, is_deductible
from app.ingest.parsing import StatementError, parse_csv
from app.services.statements import categorize_statement, link_refunds, summarize
from app.storage import db as storage

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

router = APIRouter(prefix="/api")


class Fix(BaseModel):
    category: str
    apply_to_similar: bool = True
    remember: bool = True


def _payload(statement_id: int) -> dict:
    found = storage.get_statement(statement_id)
    if found is None:
        raise HTTPException(404, "Statement not found")
    meta, items = found
    return {"statement": meta, "transactions": items, "summary": summarize(items)}


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/categories")
def categories() -> list[dict]:
    return [{"name": n, "kind": k.value, "deductible": d} for n, (k, d) in CATEGORIES.items() if n != NEEDS_REVIEW]


@router.post("/statements", status_code=201)
async def upload(file: UploadFile = File(...), sign: str = Query("auto", pattern="^(auto|bank|card)$")) -> dict:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Please upload a CSV export of your statement.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 5 MB.")
    try:
        parsed = parse_csv(content, sign)  # type: ignore[arg-type]
    except StatementError as e:
        raise HTTPException(422, str(e)) from e
    items = categorize_statement(parsed.transactions, storage.learned_rules())
    sid = storage.save_statement(file.filename or "statement.csv", parsed.sign_mode, parsed.skipped, items)
    return _payload(sid)


@router.get("/statements")
def statements() -> list[dict]:
    return storage.list_statements()


@router.get("/statements/{statement_id}")
def statement(statement_id: int) -> dict:
    return _payload(statement_id)


@router.delete("/statements/{statement_id}", status_code=204, response_class=Response)
def delete(statement_id: int) -> Response:
    if not storage.delete_statement(statement_id):
        raise HTTPException(404, "Statement not found")
    return Response(status_code=204)


@router.patch("/transactions/{transaction_id}")
def fix(transaction_id: int, body: Fix) -> dict:
    if body.category not in CATEGORIES or body.category == NEEDS_REVIEW:
        raise HTTPException(422, f"Unknown category '{body.category}'")
    sid = storage.statement_of(transaction_id)
    if sid is None:
        raise HTTPException(404, "Transaction not found")
    _, items = storage.get_statement(sid)  # type: ignore[misc]
    target = next(it for it in items if it["id"] == transaction_id)
    changed: dict[int, dict] = {}
    for it in items:
        same = bool(it["merchant"]) and it["merchant"] == target["merchant"] and (Decimal(it["amount"]) > 0) == (Decimal(target["amount"]) > 0)
        if it["id"] == transaction_id or (body.apply_to_similar and same and it["category"] == NEEDS_REVIEW):
            it.update(category=body.category, confidence=1.0, rule="user", suggestion=None,
                      reason="Set by you" if it["id"] == transaction_id else f"Same merchant as a row you fixed")
            changed[it["id"]] = it
    link_refunds(items)
    changed.update({it["id"]: it for it in items if it["category"] == "Refund"})
    storage.update_transactions(changed)
    if body.remember and target["merchant"]:
        storage.remember(learned_key(target["merchant"], Decimal(target["amount"])), body.category)
    return _payload(sid)


@router.get("/statements/{statement_id}/export.csv")
def export(statement_id: int) -> StreamingResponse:
    data = _payload(statement_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Description", "Amount", "Category", "Deductible", "Confidence", "Reason"])
    for it in data["transactions"]:
        w.writerow([it["date"], it["description"], it["amount"], it["category"],
                    "yes" if is_deductible(it["category"]) else "no", it["confidence"], it["reason"]])
    buf.seek(0)
    name = f"categorized-{statement_id}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
