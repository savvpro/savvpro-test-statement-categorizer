"""HTTP routes. Thin: validate input, call the service, shape the output."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from app.api.schemas import (
    CategoryOut,
    ConfigOut,
    CorrectionIn,
    CorrectionOut,
    StatementOut,
)
from app.brain.categories import all_categories
from app.config import ACCEPTED_EXTENSIONS, Settings
from app.domain.models import Convention
from app.errors import AppError, FileProblem
from app.services.statements import StatementService

router = APIRouter(prefix="/api")

_READ_CHUNK = 1024 * 1024


def get_service(request: Request) -> StatementService:
    return request.app.state.service  # type: ignore[no-any-return]


def get_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


ServiceDep = Annotated[StatementService, Depends(get_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=ConfigOut)
def config(settings: SettingsDep) -> ConfigOut:
    return ConfigOut(
        max_upload_mb=settings.max_upload_mb,
        accepted_extensions=list(ACCEPTED_EXTENSIONS),
        max_rows=settings.max_rows,
        max_pdf_pages=settings.max_pdf_pages,
    )


@router.get("/categories", response_model=list[CategoryOut])
def categories() -> list[CategoryOut]:
    return [CategoryOut.from_domain(c) for c in all_categories()]


def _parse_convention(value: str | None) -> Convention | None:
    if value in (None, "", "auto"):
        return None
    try:
        return Convention(value)
    except ValueError as exc:
        raise AppError(
            "amount_convention must be auto, negative_is_spending or positive_is_spending.",
            code="invalid_request",
            status_code=422,
        ) from exc


async def _read_capped(file: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise FileProblem(
                f"The upload is larger than {limit // (1024 * 1024)} MB.",
                code="file_too_large",
                status_code=413,
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/statements", response_model=StatementOut, status_code=201)
async def upload_statement(
    service: ServiceDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    amount_convention: Annotated[str | None, Form()] = None,
) -> StatementOut:
    convention = _parse_convention(amount_convention)
    data = await _read_capped(file, settings.max_upload_bytes)
    statement = await run_in_threadpool(service.upload, file.filename, data, convention)
    return StatementOut.from_domain(statement)


@router.get("/statements/{statement_id}", response_model=StatementOut)
def get_statement(statement_id: str, service: ServiceDep) -> StatementOut:
    return StatementOut.from_domain(service.get(statement_id))


@router.patch("/statements/{statement_id}/transactions/{txn_id}", response_model=CorrectionOut)
def correct_transaction(
    statement_id: str, txn_id: str, body: CorrectionIn, service: ServiceDep
) -> CorrectionOut:
    statement, updated = service.correct(
        statement_id, txn_id, body.category_id, body.apply_to_similar
    )
    return CorrectionOut(statement=StatementOut.from_domain(statement), updated_count=updated)


@router.get("/statements/{statement_id}/export.csv")
def export_statement(statement_id: str, service: ServiceDep) -> Response:
    statement = service.get(statement_id)
    stem = statement.filename.rsplit(".", 1)[0] or "statement"
    return Response(
        content=service.export_csv(statement_id),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{stem}-categorized.csv"'},
    )
