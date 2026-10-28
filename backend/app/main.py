"""Application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import categories, health, statements, transactions
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.ratelimit import configure_rate_limit
from app.core.security import (
    BodySizeLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.base import Base
from app.db.session import make_engine, make_session_factory
from app.services.ingestion import CategorizeFn


def create_app(
    settings: Settings | None = None, *, categorize: CategorizeFn | None = None
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        from app.brain.rules import load_ruleset

        app.state.ruleset = load_ruleset(settings.rules_dir)  # fail fast on bad rules
        engine = make_engine(settings.database_url)
        if settings.auto_create_tables:
            Base.metadata.create_all(engine)
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        try:
            yield
        finally:
            engine.dispose()

    docs = None if settings.is_production else "/docs"
    app = FastAPI(
        title="Ledgerly API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=docs,
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.categorize = categorize
    app.state.ruleset = None

    install_error_handlers(app)
    configure_rate_limit(app, settings.rate_limit)

    # add_middleware wraps outward: last added runs first.
    # Order at runtime: RequestID -> SecurityHeaders -> CORS -> body-size guard -> routes.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_upload_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
    )
    app.add_middleware(SecurityHeadersMiddleware, relax_csp_paths=("/docs", "/openapi.json"))
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)
    app.include_router(statements.router)
    app.include_router(transactions.router)
    app.include_router(categories.router)
    return app
