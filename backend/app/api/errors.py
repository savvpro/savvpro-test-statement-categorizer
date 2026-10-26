"""Every error leaves the API as an ErrorOut JSON body."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas import ErrorOut
from app.services.errors import DuplicateStatement, ServiceError

logger = logging.getLogger(__name__)


def _json(status_code: int, body: ErrorOut) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for error in exc.errors():
        where = ".".join(str(p) for p in error.get("loc", ()) if p not in ("body", "query", "path"))
        parts.append(f"{where}: {error.get('msg')}" if where else str(error.get("msg")))
    return "; ".join(parts) or "invalid request"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error(_request: Request, exc: ServiceError) -> JSONResponse:
        statement_id = exc.statement_id if isinstance(exc, DuplicateStatement) else None
        return _json(
            exc.status_code, ErrorOut(detail=exc.detail, code=exc.code, statement_id=statement_id)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return _json(422, ErrorOut(detail=_validation_message(exc), code="validation_error"))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _json(exc.status_code, ErrorOut(detail=str(exc.detail), code="http_error"))

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", extra={"path": request.url.path})
        return _json(500, ErrorOut(detail="internal server error", code="internal_error"))
