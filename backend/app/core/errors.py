"""AppError hierarchy and RFC 7807 problem+json handlers."""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.headers import security_headers

log = logging.getLogger("app.errors")

PROBLEM_JSON = "application/problem+json"


class AppError(StarletteHTTPException):
    """Base error. Subclasses StarletteHTTPException so FastAPI never rewraps it as a 400."""

    status = 500
    title = "Internal error"
    code = "INTERNAL"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        errors: Sequence[dict[str, Any]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(status_code=self.status, detail=detail or self.title)
        if code:
            self.code = code
        self.errors = list(errors) if errors else None
        self.extra = extra or {}


class UploadTooLarge(AppError):
    status = 413
    title = "Upload too large"
    code = "UPLOAD_TOO_LARGE"


class UnsupportedFileType(AppError):
    status = 415
    title = "Unsupported file type"
    code = "UNSUPPORTED_FILE_TYPE"


class ParseError(AppError):
    status = 422
    title = "Statement could not be parsed"
    code = "PARSE_ERROR"


class DuplicateStatement(AppError):
    status = 409
    title = "This exact file was already uploaded"
    code = "DUPLICATE_STATEMENT"


class NotFound(AppError):
    status = 404
    title = "Not found"
    code = "NOT_FOUND"


class InvalidCorrection(AppError):
    status = 422
    title = "Invalid correction"
    code = "INVALID_CORRECTION"


class RateLimited(AppError):
    status = 429
    title = "Too many requests"
    code = "RATE_LIMITED"


def problem_response(
    request: Request,
    status: int,
    title: str,
    detail: str,
    *,
    code: str | None = None,
    errors: Sequence[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body: dict[str, Any] = {
        "type": f"https://ledgerly.app/problems/{(code or 'error').lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    if code:
        body["code"] = code
    if errors:
        body["errors"] = list(errors)
    if extra:
        body.update(extra)
    # Unhandled 500s are answered by ServerErrorMiddleware, outside our middleware stack,
    # so the response itself must carry the request id and security headers.
    headers = security_headers(relaxed=False)
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


async def _app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return problem_response(
        request,
        exc.status_code,
        exc.title,
        str(exc.detail),
        code=exc.code,
        errors=exc.errors,
        extra=exc.extra,
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return problem_response(request, exc.status_code, "HTTP error", str(exc.detail))


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        {"loc": [str(p) for p in e.get("loc", ())], "message": str(e.get("msg", ""))}
        for e in exc.errors()
    ]
    return problem_response(
        request,
        422,
        "Validation error",
        "Request validation failed",
        code="VALIDATION_ERROR",
        errors=errors,
    )


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled exception", exc_info=exc)
    return problem_response(request, 500, "Internal error", "Unexpected server error")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unhandled)
