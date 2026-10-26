import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .categorizer import categorize, summarize
from .models import CategorizeResponse
from .parser import StatementError, parse_statement
from .rules import ALL_CATEGORIES

MAX_UPLOAD_BYTES = 2 * 1024 * 1024

app = FastAPI(title="Freelancer Statement Categorizer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/categorize", response_model=CategorizeResponse)
async def categorize_statement(
    file: UploadFile = File(...),
    positive_is_charge: bool = Form(False),
    overrides: str = Form("{}"),
) -> CategorizeResponse:
    """`overrides` is a JSON object {merchant_key: category} holding the user's corrections."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 2 MB.")
    try:
        parsed_overrides = json.loads(overrides)
        if not isinstance(parsed_overrides, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in parsed_overrides.items()
        ):
            raise ValueError
    except ValueError:
        raise HTTPException(422, "overrides must be a JSON object of text to text.") from None
    try:
        parsed = parse_statement(content, positive_is_charge)
    except StatementError as error:
        raise HTTPException(422, str(error)) from None

    transactions = categorize(parsed.transactions, parsed_overrides)
    return CategorizeResponse(
        transactions=transactions,
        summary=summarize(transactions),
        issues=parsed.issues,
        warnings=parsed.warnings,
        categories=ALL_CATEGORIES,
    )
