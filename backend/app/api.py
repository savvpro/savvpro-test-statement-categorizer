"""HTTP API: upload -> categorize. Stateless; nothing is persisted."""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from . import config
from .brain import categorize_statement
from .brain import rules as rules_mod
from .models import CategorizeResponse
from .parser.statement_parser import ParseError, parse_statement

logger = logging.getLogger("categorizer.api")
router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": config.APP_VERSION,
            "rules_version": rules_mod.rules_version()}


@router.get("/categories")
def categories() -> dict:
    return {"spending": [c["name"] for c in rules_mod.spending_categories()],
            "special": rules_mod.SPECIAL_BUCKETS}


@router.post("/categorize", response_model=CategorizeResponse)
async def categorize(file: UploadFile = File(...)) -> CategorizeResponse:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only .csv statements are supported in v1. "
                   "PDF parsing is on the roadmap (see DESIGN.md).",
        )
    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB).")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    try:
        parsed, meta, warnings = parse_statement(text)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    transactions, summary = categorize_statement(parsed)
    logger.info("categorized %d rows from %s (%d need review)",
                len(transactions), name, summary.review_count)

    return CategorizeResponse(
        filename=file.filename or "statement.csv",
        transactions=transactions,
        summary=summary,
        meta=meta,
        warnings=warnings,
    )
