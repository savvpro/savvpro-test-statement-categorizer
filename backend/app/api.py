from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ValidationError

from app.models import CategorizedTransaction, Category, LoanDetails
from app.parsing.csv_parser import RowError, StatementFormatError, parse_statement
from app.store import StatementSession, StatementStore, get_store
from app.summary import Summary, build_summary

router = APIRouter(prefix="/api")

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_ROWS = 10_000

# These only make sense when produced from loan details, never picked by hand.
NOT_MANUAL = {
    Category.NEEDS_REVIEW,
    Category.MORTGAGE_PAYMENT,
    Category.MORTGAGE_INTEREST,
    Category.MORTGAGE_PRINCIPAL,
}


class StatementResponse(BaseModel):
    id: str
    filename: str
    loan: LoanDetails | None
    transactions: list[CategorizedTransaction]
    parse_errors: list[RowError]
    summary: Summary


class CorrectionRequest(BaseModel):
    category: Category


def _respond(session: StatementSession) -> StatementResponse:
    return StatementResponse(
        id=session.id,
        filename=session.filename,
        loan=session.categorizer.loan,
        transactions=session.results,
        parse_errors=session.parse_errors,
        summary=build_summary(session.results),
    )


def _find(store: StatementStore, statement_id: str) -> StatementSession:
    session = store.get(statement_id)
    if session is None:
        raise HTTPException(404, "Statement not found. It may have expired; upload it again.")
    return session


def _parse_loan(text: str | None) -> LoanDetails | None:
    if not text or not text.strip():
        return None
    try:
        return LoanDetails.model_validate_json(text)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise HTTPException(422, f"Invalid loan details - {problems}") from None


@router.post("/statements", response_model=StatementResponse, status_code=201)
async def upload_statement(
    file: UploadFile = File(...),
    loan: str | None = Form(None),
    store: StatementStore = Depends(get_store),
):
    filename = file.filename or "statement.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is too large (limit 2 MB).")

    loan_details = _parse_loan(loan)

    try:
        parsed = parse_statement(content)
    except StatementFormatError as exc:
        raise HTTPException(422, str(exc)) from None

    if not parsed.transactions:
        raise HTTPException(422, "No valid transactions found in this file.")
    if len(parsed.transactions) > MAX_ROWS:
        raise HTTPException(413, f"Too many rows (limit {MAX_ROWS}).")

    session = store.create(filename, parsed.transactions, parsed.errors, loan_details)
    return _respond(session)


@router.get("/statements/{statement_id}", response_model=StatementResponse)
def get_statement(statement_id: str, store: StatementStore = Depends(get_store)):
    return _respond(_find(store, statement_id))


@router.patch(
    "/statements/{statement_id}/transactions/{transaction_id}",
    response_model=StatementResponse,
)
def correct_transaction(
    statement_id: str,
    transaction_id: int,
    body: CorrectionRequest,
    store: StatementStore = Depends(get_store),
):
    """Fix one row. The correction is remembered and applied to every
    similar row (same normalized description) in this statement."""
    session = _find(store, statement_id)
    target = next((t for t in session.results if t.id == transaction_id), None)
    if target is None:
        raise HTTPException(404, "Transaction not found.")
    if body.category in NOT_MANUAL:
        raise HTTPException(
            422,
            f"'{body.category.value}' cannot be chosen by hand. Mortgage splits come "
            "from your loan details, and 'Needs Review' means undecided.",
        )
    session.categorizer.learn(target.description, body.category)
    session.recompute()
    return _respond(session)


@router.put("/statements/{statement_id}/loan", response_model=StatementResponse)
def set_loan(
    statement_id: str,
    loan: LoanDetails,
    store: StatementStore = Depends(get_store),
):
    """Add or change the loan details after upload; mortgage rows are re-split."""
    session = _find(store, statement_id)
    session.set_loan(loan)
    return _respond(session)