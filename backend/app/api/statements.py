from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import AppSettings, DbSession
from app.ingest.formats import IngestError
from app.schemas import StatementDetail, StatementOut, StatementSummary
from app.services import export as export_service
from app.services import statements as statement_service
from app.services import summary as summary_service

router = APIRouter(prefix="/statements", tags=["statements"])


@router.post("", response_model=StatementDetail, status_code=201)
def upload_statement(file: UploadFile, db: DbSession, settings: AppSettings) -> StatementDetail:
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    content = file.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413, detail=f"File is larger than {settings.max_upload_mb} MB"
        )
    try:
        statement = statement_service.ingest_statement(db, filename, content)
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return statement_service.statement_detail(db, statement.id)


@router.get("", response_model=list[StatementOut])
def list_statements(db: DbSession) -> list[StatementOut]:
    return statement_service.list_statements(db)


@router.get("/{statement_id}", response_model=StatementDetail)
def get_statement(statement_id: int, db: DbSession) -> StatementDetail:
    return statement_service.statement_detail(db, statement_id)


@router.get("/{statement_id}/summary", response_model=StatementSummary)
def get_summary(statement_id: int, db: DbSession) -> StatementSummary:
    return summary_service.summary(db, statement_id)


@router.get("/{statement_id}/export")
def export_statement(statement_id: int, db: DbSession) -> Response:
    filename, content = export_service.export_csv(db, statement_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
