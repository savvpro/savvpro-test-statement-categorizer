"""Application factory: wires configuration, adapters and services together."""
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import router
from .categorization.factory import build_engine
from .categorization.rulebook import RuleBook
from .config import Settings
from .domain.errors import DomainError, FileTooLargeError, UnsupportedFormatError
from .ingestion.base import ReaderRegistry
from .ingestion.csv_reader import CsvStatementReader
from .learning.repository import JsonFileMerchantRuleRepository, MerchantRuleRepository
from .services.statement_service import MerchantRuleService, StatementService

logger = logging.getLogger("categorizer")

_ERROR_STATUS = {UnsupportedFormatError: 415, FileTooLargeError: 413}


def create_app(settings: Optional[Settings] = None,
               rule_repository: Optional[MerchantRuleRepository] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    rule_repository = rule_repository or JsonFileMerchantRuleRepository(settings.rules_store_path)
    engine = build_engine(settings, RuleBook.load(), rule_repository)
    readers = ReaderRegistry([CsvStatementReader(max_rows=settings.max_rows)])

    app = FastAPI(title="Statement Categorizer", version="1.1.0")
    app.state.settings = settings
    app.state.statement_service = StatementService(readers, engine, settings.max_upload_bytes)
    app.state.rule_service = MerchantRuleService(rule_repository)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status = _ERROR_STATUS.get(type(exc), 422)
        logger.info("Rejected request: %s (%s)", exc, status)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    app.include_router(router)
    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = create_app()
