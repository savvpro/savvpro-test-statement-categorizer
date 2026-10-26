import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import router
from .brain.categorizer import Categorizer
from .brain.rules import load_rules
from .config import Settings, get_settings
from .services.statements import NotFoundError, StatementService
from .store import StatementStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = FastAPI(title="Statement Categorizer", version="1.0.0")
    app.state.settings = settings
    app.state.service = StatementService(
        store=StatementStore(settings.max_statements),
        categorizer=Categorizer(load_rules(settings.rules_path)),
        max_rows=settings.max_rows,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    app.include_router(router, prefix="/api")
    return app


app = create_app()
