import csv
import io
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .database import initialize, read_snapshot
from .domain import CATEGORIES, KIND_CATEGORIES, MAX_FILE_BYTES, ImportOptions, ReviewRequest
from .importer import ImportFailure, preview
from .service import (
    delete_statement,
    get_statement,
    get_transactions,
    import_statement,
    review_transaction,
    statement_summary,
    storage_error_handler,
)
from .summaries import summarize

ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(_app):
    initialize()
    yield


app = FastAPI(title="LedgerLens", version="1.0.0", lifespan=lifespan)
app.add_exception_handler(sqlite3.OperationalError, storage_error_handler)


@app.exception_handler(ImportFailure)
async def import_error(_request, exc: ImportFailure):
    return JSONResponse(status_code=422, content={"detail": str(exc), "errors": exc.errors})


@app.middleware("http")
async def local_security(request: Request, call_next):
    # Local app: reject cross-site browser writes (no wildcard CORS).
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
        from urllib.parse import urlsplit

        parsed = urlsplit(origin)
        if parsed.hostname not in ("localhost", "127.0.0.1", "[::1]", "::1", "testserver"):
            return JSONResponse(
                status_code=403, content={"detail": "Cross-site writes are disabled."}
            )
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_FILE_BYTES + 64 * 1024:
        return JSONResponse(status_code=413, content={"detail": "File exceeds the 2 MiB limit."})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


async def read_upload(file: UploadFile):
    try:
        content = await file.read(MAX_FILE_BYTES + 1)
    finally:
        await file.close()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds the 2 MiB limit.")
    return content


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "LedgerLens"}


@app.get("/api/categories")
def categories():
    return {"categories": CATEGORIES, "kind_categories": KIND_CATEGORIES}


@app.get("/api/demo")
def demo():
    return Response(
        (ROOT / "samples" / "consultant-demo.csv").read_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="consultant-demo.csv"'},
    )


@app.post("/api/imports/preview")
async def preview_upload(file: Annotated[UploadFile, File()]):
    return preview(await read_upload(file))


@app.post("/api/statements")
async def create_statement(file: Annotated[UploadFile, File()], options: Annotated[str, Form()]):
    try:
        config = ImportOptions.model_validate_json(options)
    except ValidationError as exc:
        raise HTTPException(
            422,
            "Invalid import settings: " + "; ".join(str(error["msg"]) for error in exc.errors()),
        ) from exc
    filename = (file.filename or "statement.csv").replace("\\", "/").split("/")[-1][:200]
    return import_statement(await read_upload(file), filename, config)


@app.get("/api/statements")
def list_statements():
    with read_snapshot() as conn:
        rows = conn.execute(
            "SELECT id FROM statements ORDER BY created_at DESC, rowid DESC"
        ).fetchall()
        return [
            {
                "statement": get_statement(conn, row["id"]),
                "summary": statement_summary(conn, row["id"]),
            }
            for row in rows
        ]


@app.get("/api/statements/{statement_id}")
def statement(statement_id: str):
    with read_snapshot() as conn:
        return get_statement(conn, statement_id)


@app.get("/api/statements/{statement_id}/workspace")
def workspace(statement_id: str):
    with read_snapshot() as conn:
        metadata = get_statement(conn, statement_id)
        rows = get_transactions(conn, statement_id)
        report = {**summarize(rows), "currency": metadata["currency"]}
        return {"statement": metadata, "transactions": rows, "summary": report}


@app.get("/api/statements/{statement_id}/transactions")
def transactions(
    statement_id: str,
    search: str = "",
    status: Literal["all", "needs_review", "reviewed", "categorized", "excluded"] = "all",
    category: str = "",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=5000)] = 100,
):
    with read_snapshot() as conn:
        get_statement(conn, statement_id)
        rows = get_transactions(conn, statement_id)
    if search:
        rows = [r for r in rows if search.casefold() in r["description"].casefold()]
    if category:
        rows = [r for r in rows if r["category"] == category]
    if status != "all":

        def matches(row):
            if status == "excluded":
                return row["duplicate_status"] == "excluded"
            if status == "needs_review":
                return row["needs_review"]
            return (
                not row["needs_review"]
                and row["duplicate_status"] != "excluded"
                and row["reviewed"] == (status == "reviewed")
            )

        rows = [r for r in rows if matches(r)]
    return {"items": rows[offset : offset + limit], "total": len(rows)}


@app.patch("/api/transactions/{transaction_id}/review")
def review(transaction_id: str, body: ReviewRequest):
    return review_transaction(transaction_id, body)


@app.get("/api/transactions/{transaction_id}/history")
def history(transaction_id: str):
    with read_snapshot() as conn:
        if not conn.execute(
            "SELECT id FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone():
            raise HTTPException(404, "Transaction not found.")
        return [
            dict(r)
            for r in conn.execute(
                """SELECT action, created_at, before_json, after_json
            FROM review_events WHERE transaction_id = ? ORDER BY id""",
                (transaction_id,),
            )
        ]


@app.get("/api/statements/{statement_id}/summary")
def summary(statement_id: str):
    with read_snapshot() as conn:
        return statement_summary(conn, statement_id)


def safe_text(value):
    text = str(value)
    if text.lstrip().lstrip("\ufeff").lstrip().startswith(
        ("=", "+", "-", "@", "\t", "\r", "\n")
    ) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def decimal_text(amount: int):
    sign = "-" if amount < 0 else ""
    whole, fraction = divmod(abs(amount), 100)
    return f"{sign}{whole}.{fraction:02d}"


@app.get("/api/statements/{statement_id}/export")
def export(
    statement_id: str,
    kind: Literal["transactions", "summary"] = "transactions",
    reviewed_only: bool = False,
):
    with read_snapshot() as conn:
        statement = get_statement(conn, statement_id)
        rows = get_transactions(conn, statement_id)
        report = {**summarize(rows), "currency": statement["currency"]}
    if reviewed_only and report["provisional"]:
        raise HTTPException(409, "Resolve every review item before exporting a reviewed statement.")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    if kind == "transactions":
        writer.writerow(
            [
                "source_row",
                "date",
                "description",
                "amount",
                "currency",
                "kind",
                "category",
                "status",
                "duplicate_status",
                "included",
                "explanation",
                "rule_ids",
                "engine_version",
            ]
        )
        for row in rows:
            state = (
                "excluded"
                if row["duplicate_status"] == "excluded"
                else "needs_review"
                if row["needs_review"]
                else "reviewed"
                if row["reviewed"]
                else "categorized"
            )
            writer.writerow(
                [
                    row["source_row"],
                    row["date"],
                    safe_text(row["description"]),
                    decimal_text(row["amount_minor"]),
                    statement["currency"],
                    row["kind"],
                    CATEGORIES[row["category"]],
                    state,
                    row["duplicate_status"],
                    state != "excluded",
                    safe_text(
                        "User-confirmed classification."
                        if row["reviewed"]
                        else row["decision"]["explanation"]
                    ),
                    ", ".join(row["decision"]["rule_ids"]),
                    row["decision"]["engine_version"],
                ]
            )
    else:
        writer.writerow(["section", "metric", "amount", "currency", "provisional"])
        for key, value in report["totals"].items():
            writer.writerow(
                [
                    "totals",
                    key.removesuffix("_minor"),
                    decimal_text(value),
                    statement["currency"],
                    report["provisional"],
                ]
            )
        for category in report["categories"]:
            writer.writerow(
                [
                    "category_net",
                    category["label"],
                    decimal_text(category["net_minor"]),
                    statement["currency"],
                    report["provisional"],
                ]
            )
    return Response(
        "\ufeff" + stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="ledgerlens-{kind}-{statement_id[:8]}.csv"'
            )
        },
    )


@app.delete("/api/statements/{statement_id}", status_code=204)
def remove_statement(statement_id: str):
    delete_statement(statement_id)


# Production: build frontend first, then start the same backend process.
frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
