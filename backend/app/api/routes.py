from pathlib import Path, PurePath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from ..categories import ASSIGNABLE, KIND, Category
from ..config import Settings
from ..parser import StatementParseError
from ..services.export import statement_to_csv
from ..services.statements import StatementService
from ..services.summary import summarize
from .schemas import CategoryInfo, FixRequest, FixResponse, StatementOut

router = APIRouter()

SAMPLE_PATH = Path(__file__).resolve().parents[2] / "sample_data" / "driver_statement.csv"


def get_service(request: Request) -> StatementService:
    return request.app.state.service


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


Service = Annotated[StatementService, Depends(get_service)]
Config = Annotated[Settings, Depends(get_settings)]


def _to_out(statement, settings: Settings) -> StatementOut:
    return StatementOut(
        id=statement.id,
        filename=statement.filename,
        currency=settings.currency,
        categories=[CategoryInfo(name=c, kind=KIND[c]) for c in Category],
        created_at=statement.created_at,
        transactions=statement.transactions,
        skipped=statement.skipped,
        warnings=statement.warnings,
        summary=summarize(statement.transactions),
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/categories", response_model=list[CategoryInfo])
def categories() -> list[CategoryInfo]:
    """The categories a user may assign when fixing a row."""
    return [CategoryInfo(name=c, kind=KIND[c]) for c in ASSIGNABLE]


@router.get("/sample-statement")
def sample_statement() -> FileResponse:
    return FileResponse(SAMPLE_PATH, media_type="text/csv", filename="driver_statement.csv")


@router.post("/statements", response_model=StatementOut, status_code=201)
async def upload_statement(
    file: UploadFile,
    service: Service,
    settings: Config,
    purchases_positive: bool = False,
) -> StatementOut:
    name = PurePath(file.filename or "statement.csv").name[:120]
    if not name.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")

    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            413, f"That file is too large (limit {settings.max_upload_bytes // 1_000_000} MB)."
        )
    try:
        statement = await run_in_threadpool(
            service.create, name, content, purchases_positive=purchases_positive
        )
    except StatementParseError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _to_out(statement, settings)


@router.get("/statements/{statement_id}", response_model=StatementOut)
def get_statement(statement_id: str, service: Service, settings: Config) -> StatementOut:
    return _to_out(service.get(statement_id), settings)


@router.patch(
    "/statements/{statement_id}/transactions/{transaction_id}", response_model=FixResponse
)
def fix_transaction(
    statement_id: str,
    transaction_id: str,
    body: FixRequest,
    service: Service,
    settings: Config,
) -> FixResponse:
    result = service.fix(statement_id, transaction_id, body.category)
    return FixResponse(
        statement=_to_out(result.statement, settings), updated_ids=result.updated_ids
    )


@router.get("/statements/{statement_id}/export.csv")
def export_statement(statement_id: str, service: Service) -> Response:
    statement = service.get(statement_id)
    return Response(
        content=statement_to_csv(statement),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="categorized-{statement.id[:8]}.csv"'
        },
    )
