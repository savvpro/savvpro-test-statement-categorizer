"""HTTP boundary. Run from the repository root: uvicorn backend.app.main:app."""

import hashlib
import json
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.app.engine import CATEGORIES, EXPENSE_CATEGORIES
from backend.app.parser import MAX_BYTES, StatementError, parse_csv
from backend.app.repository import ConflictError, NotFoundError, Repository
from backend.app.service import add_summary, export_csv

ROOT = Path(__file__).resolve().parents[2]


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(min_length=1, max_length=50)
    kind: Literal["expense", "refund", "income", "transfer", "personal", "excluded"]
    note: str = Field(default="", max_length=500)
    revision: int = Field(ge=0)


def create_app(database_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="Ledgerly API", version="1.0.0")
    repository = Repository(
        database_path
        or Path(
            os.environ.get(
                "LEDGERLY_DB",
                str(ROOT / "data" / "ledgerly.db"),
            )
        )
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "testserver", "*.onrender.com"],
    )

    @app.middleware("http")
    async def local_request_guard(request: Request, call_next):
        if request.method in ("POST", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            allowed_origins = {
                str(request.base_url).rstrip("/"),
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            }
            if origin and origin not in allowed_origins:
                return JSONResponse({"detail": "Cross-origin writes are not allowed."}, 403)
            length = request.headers.get("content-length")
            try:
                length = int(length) if length else 0
            except ValueError:
                return JSONResponse({"detail": "Invalid request length."}, 400)
            if length > MAX_BYTES + 128 * 1024:
                return JSONResponse({"detail": "File exceeds the 5 MB limit."}, 413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/statements"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(StatementError)
    async def statement_error(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(NotFoundError)
    async def not_found(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ConflictError)
    async def conflict(_request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/api/categories")
    def categories():
        return {"categories": CATEGORIES, "expense_categories": EXPENSE_CATEGORIES}

    @app.get("/api/samples/{name}")
    def sample(name: str):
        if name not in (
            "freelancer_statement.csv",
            "debit_credit_statement.csv",
            "invalid_statement.csv",
        ):
            raise NotFoundError("Sample not found.")
        return FileResponse(ROOT / "sample_data" / name, media_type="text/csv", filename=name)

    @app.get("/api/statements")
    def list_statements():
        return repository.list_statements()

    @app.post("/api/statements")
    async def import_statement(
        file: Annotated[UploadFile, File()],
        currency: Annotated[str, Form()] = "USD",
        date_format: Annotated[str, Form()] = "ISO",
        amount_convention: Annotated[str, Form()] = "negative_expense",
    ):
        try:
            filename = (file.filename or "statement.csv").replace("\\", "/").split("/")[-1]
            if not filename.lower().endswith(".csv") or len(filename) > 200:
                raise StatementError("Upload a .csv file with a filename under 200 characters.")
            content = await file.read(MAX_BYTES + 1)
            options = {
                "currency": currency,
                "date_format": date_format,
                "amount_convention": amount_convention,
            }
            parsed = parse_csv(content, **options)
            fingerprint = hashlib.sha256(
                content + json.dumps(options, sort_keys=True).encode(),
            ).hexdigest()
            statement_id, created = repository.import_statement(
                parsed,
                filename,
                fingerprint,
                options,
            )
            result = add_summary(repository.get_statement(statement_id))
            result["already_imported"] = not created
            return JSONResponse(result, status_code=201 if created else 200)
        finally:
            await file.close()

    @app.get("/api/statements/{statement_id}")
    def statement(statement_id: str):
        return add_summary(repository.get_statement(statement_id))

    @app.patch("/api/statements/{statement_id}/transactions/{transaction_id}")
    def review(statement_id: str, transaction_id: str, payload: ReviewRequest):
        repository.review(statement_id, transaction_id, **payload.model_dump())
        return add_summary(repository.get_statement(statement_id))

    @app.get("/api/statements/{statement_id}/export")
    def export(statement_id: str):
        statement = repository.get_statement(statement_id)
        return Response(
            export_csv(statement),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="ledgerly-{statement_id[:8]}.csv"',
            },
        )

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
