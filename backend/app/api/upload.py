from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.brain.categorizer import categorize
from app.brain.rules_loader import load_rules
from app.config import MAX_UPLOAD_BYTES
from app.parser.csv_parser import ParseError, parse_csv
from app.schemas import UploadResponse
from app.services.store import StatementStore, get_store
from app.services.summary import build_summary

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(
    file: UploadFile = File(...),
    store: StatementStore = Depends(get_store),
):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 2 MB)")

    try:
        transactions, skipped = parse_csv(content)
    except ParseError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not transactions:
        raise HTTPException(400, "No valid transactions found in file")

    rules = load_rules()
    categorize(transactions, rules)
    store.replace(transactions)
    return UploadResponse(
        transactions=transactions,
        skipped=skipped,
        summary=build_summary(transactions, rules),
    )