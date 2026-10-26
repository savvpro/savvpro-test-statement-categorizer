"""Application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.api.routes import router
from app.brain.classifier import Classifier
from app.brain.rules import RuleTable
from app.config import Settings
from app.errors import AppError
from app.middleware import (
    BodyLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    error_response,
)
from app.services.statements import StatementService
from app.storage.repository import InMemoryStatementRepository, StatementRepository
from app.storage.user_rules import UserRuleStore

logger = logging.getLogger("statement_categorizer")


def create_app(
    settings: Settings | None = None,
    *,
    repository: StatementRepository | None = None,
    user_rules: UserRuleStore | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    rules = user_rules if user_rules is not None else UserRuleStore(settings.user_rules_path)
    classifier = Classifier(RuleTable.load(), rules)
    repo = repository or InMemoryStatementRepository(settings.max_stored_statements)

    app = FastAPI(title="Statement Categorizer", version="1.0.0")
    app.state.settings = settings
    app.state.service = StatementService(settings, repo, classifier, rules)

    _install_error_handlers(app)
    app.include_router(router)

    # Middleware added last runs first: CORS answers preflights before anything is counted.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodyLimitMiddleware, max_body_bytes=settings.max_upload_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        uploads_per_minute=settings.rate_limit_uploads_per_minute,
        requests_per_minute=settings.rate_limit_requests_per_minute,
        trust_proxy_headers=settings.trust_proxy_headers,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
        expose_headers=["Retry-After", "Content-Disposition"],
    )
    return app


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
        message = f"Invalid request: {where or 'body'}: {first.get('msg', 'invalid value')}"
        return error_response(422, "invalid_request", message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return error_response(500, "internal_error", "Something went wrong on our side.")


app = create_app()
