"""HTTP boundary. The same FastAPI process can serve the compiled React application."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .domain import CURRENCIES, AmountMode, Category, DateFormat, ImportOptions, Kind
from .parser import MAX_FILE_BYTES, StatementError, parse_statement
from .reporting import export_summary, export_transactions, summarize
from .store import ConflictError, Store

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RequestBoundary:
    """Bound the whole multipart body before parsing; reject untrusted browser writes.

    Content-Length is only an early optimization. Count received bytes as well, so
    chunked requests cannot bypass the limit. This application is single-user/local.
    """

    def __init__(self, app, origins: set[str]):
        self.app, self.origins = app, origins

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PATCH", "DELETE", "PUT"}:
            return await self.app(scope, receive, send)
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        origin = headers.get(b"origin", b"").decode("latin-1")
        if origin and origin not in self.origins:
            return await JSONResponse({"detail": "This origin is not allowed."}, status_code=403)(scope, receive, send)
        limit = MAX_FILE_BYTES + 64 * 1024
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)(scope, receive, send)
        if declared > limit:
            return await JSONResponse({"detail": "Upload exceeds 5 MiB plus form overhead."}, status_code=413)(
                scope, receive, send
            )
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > limit:
                return await JSONResponse({"detail": "Upload exceeds 5 MiB plus form overhead."}, status_code=413)(
                    scope, receive, send
                )
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body, delivered = b"".join(chunks), False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: Category
    kind: Kind
    excluded: bool = False
    note: str = Field(default="", max_length=1000)
    expected_version: int = Field(ge=1, strict=True)


def create_app(db_path: Path | None = None, static_dir: Path | None = None) -> FastAPI:
    store = Store(db_path or Path(os.getenv("LEDGER_DB_PATH", PROJECT_ROOT / "data" / "ledger.sqlite3")))
    origins = {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await run_in_threadpool(store.initialize)
        yield

    app = FastAPI(title="Ledgerly API", version="1.0.0", lifespan=lifespan)
    app.state.store = store
    app.add_middleware(RequestBoundary, origins=origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(origins),
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
            )
        return response

    @app.exception_handler(StatementError)
    async def invalid_statement(request, exc: StatementError):
        return JSONResponse(status_code=422, content={"detail": exc.message, "errors": exc.errors})

    @app.exception_handler(ConflictError)
    async def conflict(request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    def require_statement(statement_id: str) -> dict:
        statement = store.get_statement(statement_id)
        if not statement:
            raise HTTPException(404, "Statement not found.")
        return statement

    @app.get("/api/health")
    def health():
        return {"status": "ok", "engine": "deterministic-rules", "version": "1.0.0"}

    @app.get("/api/options")
    def options():
        return {"categories": list(Category), "kinds": list(Kind), "currencies": CURRENCIES}

    @app.get("/api/sample")
    def sample():
        return Response(
            (PROJECT_ROOT / "samples" / "designer-bank.csv").read_bytes(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="designer-bank.csv"'},
        )

    @app.get("/api/statements")
    def list_statements():
        return store.list_statements()

    @app.post("/api/statements")
    async def upload(
        file: Annotated[UploadFile, File()],
        currency: Annotated[str, Form()] = "USD",
        amount_mode: Annotated[AmountMode, Form()] = AmountMode.BANK,
        date_format: Annotated[DateFormat, Form()] = DateFormat.ISO,
    ):
        try:
            if not file.filename or not file.filename.lower().endswith(".csv"):
                raise HTTPException(415, "Upload a CSV export. PDF, images, and spreadsheets are not supported.")
            content = await file.read(MAX_FILE_BYTES + 1)
        finally:
            await file.close()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(413, "CSV files must be no larger than 5 MiB.")
        settings = ImportOptions(currency.upper(), amount_mode, date_format)
        parsed = await run_in_threadpool(parse_statement, content, settings)
        # A filename is metadata only: it is never used as a filesystem path.
        filename = Path(file.filename.replace("\\", "/")).name[:120]
        statement_id, reused = await run_in_threadpool(store.import_statement, filename, content, settings, parsed)
        return JSONResponse({"id": statement_id, "reused": reused}, status_code=200 if reused else 201)

    @app.get("/api/statements/{statement_id}")
    def get_statement(statement_id: str):
        statement = require_statement(statement_id)
        return {**statement, "summary": summarize(statement["transactions"])}

    @app.patch("/api/transactions/{transaction_id}")
    def review(transaction_id: str, payload: ReviewInput):
        try:
            result = store.review(transaction_id, payload.model_dump())
        except ConflictError:
            raise
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if result is None:
            raise HTTPException(404, "Transaction not found.")
        return result

    @app.get("/api/statements/{statement_id}/export")
    def export(statement_id: str, final: bool = False, summary: bool = False):
        statement = require_statement(statement_id)
        if final and summarize(statement["transactions"])["review_count"]:
            raise HTTPException(409, "Resolve every Needs Review row before exporting a final report.")
        name = ("final" if final else "draft") + ("-summary.csv" if summary else "-transactions.csv")
        content = export_summary(statement) if summary else export_transactions(statement)
        return Response(
            "\ufeff" + content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )

    @app.get("/api/statements/{statement_id}/audit")
    def audit(statement_id: str):
        require_statement(statement_id)
        return store.audit(statement_id)

    @app.delete("/api/statements/{statement_id}", status_code=204)
    def delete(statement_id: str):
        if not store.delete_statement(statement_id):
            raise HTTPException(404, "Statement not found.")
        return Response(status_code=204)

    # API routes come first; unknown /api routes must not return the React index.
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PATCH", "DELETE", "PUT"])
    def missing_api(path: str):
        raise HTTPException(404, "API route not found.")

    dist = static_dir or PROJECT_ROOT / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
