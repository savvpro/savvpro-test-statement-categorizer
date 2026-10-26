import csv
import io

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from app.api.schemas import (
    CorrectionIn,
    CorrectionOut,
    SummaryOut,
    TransactionOut,
    UploadOut,
)
from app.core.parser import parse_csv
from app.services.store import ASSIGNABLE_CATEGORIES, Row, Session, store
from app.services.summary import summarize

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value: str) -> str:
    """Neutralize spreadsheet formula injection in text cells."""
    if value and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _session_or_404(upload_id: str) -> Session:
    session = store.get(upload_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    return session


def _row_or_404(session: Session, row_id: int) -> Row:
    row = session.rows.get(row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return row


def _to_out(row_id: int, row: Row) -> TransactionOut:
    r = row.result
    t = r.transaction
    return TransactionOut(
        id=row_id,
        row_number=t.row_number,
        date=t.txn_date,
        description=t.description,
        amount=t.amount,
        currency=t.currency,
        category=r.category,
        confidence=r.confidence,
        reason=r.reason,
        needs_review=r.needs_review,
        matched_rule=r.matched_rule,
        errors=t.errors,
        is_duplicate=row.is_duplicate,
        duplicate_of=row.duplicate_of,
        user_corrected=row.user_corrected,
    )


def _upload_out(session: Session) -> UploadOut:
    return UploadOut(
        upload_id=session.id,
        filename=session.filename,
        summary=summarize(session),
        transactions=[_to_out(i, row) for i, row in session.rows.items()],
    )


@router.post("/uploads", response_model=UploadOut, status_code=201)
async def create_upload(file: UploadFile = File(...)) -> UploadOut:
    filename = file.filename or "upload.csv"
    is_csv = filename.lower().endswith(".csv") or file.content_type == "text/csv"
    if not is_csv:
        raise HTTPException(status_code=415, detail="Only CSV files are supported")

    content = await file.read()
    if not content.strip():
        raise HTTPException(status_code=400, detail="The file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large (max 5 MB)")

    try:
        txns = parse_csv(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {exc}") from exc
    if not txns:
        raise HTTPException(status_code=400, detail="No transaction rows found")

    session = store.create(filename, txns)
    return _upload_out(session)


@router.get("/uploads/{upload_id}", response_model=UploadOut)
def get_upload(upload_id: str) -> UploadOut:
    return _upload_out(_session_or_404(upload_id))


@router.get("/uploads/{upload_id}/summary", response_model=SummaryOut)
def get_summary(upload_id: str) -> SummaryOut:
    return summarize(_session_or_404(upload_id))


@router.patch(
    "/uploads/{upload_id}/transactions/{row_id}", response_model=CorrectionOut
)
def correct_transaction(upload_id: str, row_id: int, body: CorrectionIn) -> CorrectionOut:
    session = _session_or_404(upload_id)

    if body.category is not None and body.category not in ASSIGNABLE_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown category. Choose one of: {', '.join(ASSIGNABLE_CATEGORIES)}",
        )

    row = _row_or_404(session, row_id)

    also_updated = 0
    if body.category is not None:
        if not row.result.transaction.is_valid:
            raise HTTPException(
                status_code=409, detail="This row could not be read, so it cannot be categorized"
            )
        also_updated = store.correct(session, row_id, body.category)
    if body.keep_duplicate is not None:
        store.set_keep_duplicate(row, body.keep_duplicate)

    return CorrectionOut(
        transaction=_to_out(row_id, row),
        also_updated=also_updated,
        summary=summarize(session),
    )


@router.get("/uploads/{upload_id}/export.csv")
def export_csv(upload_id: str) -> Response:
    session = _session_or_404(upload_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["date", "description", "amount", "currency", "category",
         "confidence", "needs_review", "duplicate", "reason"]
    )
    for row in session.rows.values():
        r = row.result
        t = r.transaction
        writer.writerow([
            t.txn_date.isoformat() if t.txn_date else "",
            _csv_safe(t.description),
            str(t.amount) if t.amount is not None else "",
            t.currency,
            _csv_safe(r.category),
            f"{r.confidence:.2f}",
            "yes" if r.needs_review else "no",
            "yes" if row.is_duplicate else "no",
            _csv_safe(r.reason),
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{session.filename}.categorized.csv"'},
    )


@router.get("/categories", response_model=list[str])
def list_categories() -> list[str]:
    return ASSIGNABLE_CATEGORIES
