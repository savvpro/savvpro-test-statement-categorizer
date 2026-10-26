"""Uniform error envelope and exception handlers."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: object = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, id: object):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} {id!r} not found",
            status=404,
        )


class ConflictError(AppError):
    def __init__(self, message: str, details: object = None):
        super().__init__(code="CONFLICT", message=message, status=409, details=details)


class ValidationError(AppError):
    def __init__(self, message: str, details: object = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status=422, details=details)


def _envelope(code: str, message: str, details: object = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content=_envelope(exc.code, exc.message, exc.details),
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_envelope("INTERNAL_ERROR", "An unexpected error occurred"),
    )
