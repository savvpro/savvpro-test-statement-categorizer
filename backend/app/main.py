"""FastAPI application factory."""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import (
    accounts,
    categories,
    dashboard,
    demo,
    health,
    imports,
    reports,
    review,
    rules,
    statements,
    transactions,
)
from app.core.config import settings
from app.core.db import create_tables
from app.core.errors import AppError, app_error_handler, generic_error_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    yield


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request-ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# Error handlers
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_error_handler)

# Routers
PREFIX = "/api/v1"
for router in [
    health.router,
    accounts.router,
    imports.router,
    statements.router,
    transactions.router,
    review.router,
    rules.router,
    categories.router,
    dashboard.router,
    reports.router,
    demo.router,
]:
    app.include_router(router, prefix=PREFIX)
