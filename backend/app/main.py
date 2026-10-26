from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .brain import categories as cats
from .config import Settings
from .db import Database
from .ingest.reader import SignConvention, StatementParseError
from .schemas import (
    CategoryOut,
    RuleOut,
    SampleOut,
    StatementListItem,
    StatementOut,
    TransactionUpdate,
)
from .services import InvalidInputError, NotFoundError, StatementService

logger = logging.getLogger("driveledger")

ALLOWED_EXTENSIONS = {".csv", ".txt", ".ofx", ".qfx"}

# Fake demo statements shipped in /samples. Keyed by a fixed name so users can't
# request arbitrary paths.
SAMPLES: dict[str, tuple[str, str, str]] = {
    "checking": (
        "gig_driver_checking.csv",
        "Checking account (Q1)",
        "Bank export with payouts, refunds, transfers, a duplicate row and pending items.",
    ),
    "credit_card": (
        "gig_driver_credit_card.csv",
        "Credit card (Q1)",
        "Card export where charges are positive, with a preamble and a total line.",
    ),
}

api = APIRouter(prefix="/api")


def get_service(request: Request) -> StatementService:
    return request.app.state.service


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/categories", response_model=list[CategoryOut])
def list_categories() -> list[CategoryOut]:
    return [
        CategoryOut(
            id=c.id,
            label=c.label,
            kind=c.kind.value,
            schedule_c_line=c.schedule_c_line,
            description=c.description,
        )
        for c in cats.CATEGORIES
    ]


@api.get("/statements", response_model=list[StatementListItem])
def list_statements(service: StatementService = Depends(get_service)):
    return service.list_statements()


@api.post("/statements", response_model=StatementOut, status_code=201)
async def upload_statement(
    file: UploadFile = File(...),
    sign_convention: SignConvention = Form(SignConvention.AUTO),
    service: StatementService = Depends(get_service),
    settings: Settings = Depends(get_settings),
):
    filename = Path(file.filename or "statement.csv").name
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Please upload a CSV, OFX or QFX statement export.")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "The file is too large.")
    statement_id = service.import_statement(filename, data, sign_convention)
    logger.info("Imported statement %s (%s bytes)", statement_id, len(data))
    return service.get_statement(statement_id)


@api.get("/statements/{statement_id}", response_model=StatementOut)
def get_statement(statement_id: int, service: StatementService = Depends(get_service)):
    return service.get_statement(statement_id)


@api.delete("/statements/{statement_id}", status_code=204)
def delete_statement(statement_id: int, service: StatementService = Depends(get_service)):
    service.delete_statement(statement_id)
    return Response(status_code=204)


@api.patch("/statements/{statement_id}/transactions/{tx_id}", response_model=StatementOut)
def update_transaction(
    statement_id: int,
    tx_id: int,
    body: TransactionUpdate,
    service: StatementService = Depends(get_service),
):
    return service.update_transaction(statement_id, tx_id, body.category, body.remember)


@api.get("/statements/{statement_id}/export.csv")
def export_statement(statement_id: int, service: StatementService = Depends(get_service)):
    content = service.export_csv(statement_id)
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="statement-{statement_id}.csv"'},
    )


@api.get("/rules", response_model=list[RuleOut])
def list_rules(service: StatementService = Depends(get_service)):
    return service.list_rules()


@api.delete("/rules/{direction}/{merchant_key}", status_code=204)
def delete_rule(
    direction: str, merchant_key: str, service: StatementService = Depends(get_service)
):
    service.delete_rule(merchant_key, direction)
    return Response(status_code=204)


@api.get("/samples", response_model=list[SampleOut])
def list_samples() -> list[SampleOut]:
    return [SampleOut(name=k, title=v[1], description=v[2]) for k, v in SAMPLES.items()]


@api.post("/samples/{name}", response_model=StatementOut, status_code=201)
def import_sample(
    name: str,
    service: StatementService = Depends(get_service),
    settings: Settings = Depends(get_settings),
):
    if name not in SAMPLES:
        raise HTTPException(404, "Unknown sample.")
    path = settings.samples_dir / SAMPLES[name][0]
    statement_id = service.import_statement(path.name, path.read_bytes())
    return service.get_statement(statement_id)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="DriveLedger API",
        version="1.0.0",
        description="Sorts a gig driver's bank and card transactions into Schedule C categories.",
    )
    app.state.settings = settings
    app.state.service = StatementService(
        Database(settings.database_path), threshold=settings.review_threshold
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(InvalidInputError)
    async def _invalid(_: Request, exc: InvalidInputError):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(StatementParseError)
    async def _unreadable(_: Request, exc: StatementParseError):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    app.include_router(api)
    return app
