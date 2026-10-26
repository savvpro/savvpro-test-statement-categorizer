from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from app.api import categories, health, rules, samples, statements, transactions
from app.api.errors import register_error_handlers
from app.config import Settings, get_settings
from app.db import session as db_session
from app.logging import configure_logging


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        db_session.init_db(engine or db_session.engine)
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (health, categories, statements, transactions, rules, samples):
        app.include_router(module.router, prefix="/api")
    register_error_handlers(app)

    return app


app = create_app()
