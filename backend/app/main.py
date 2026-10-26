import logging
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from . import service, storage
from .categorizer.rules import load_rulebook
from .config import Settings
from .parsing.ocr import ocr_available

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class CorrectionIn(BaseModel):
    category: str | None = Field(description="New category, or null to let the rules decide again")


class RuleIn(BaseModel):
    pattern: str = Field(min_length=1, max_length=80)
    match_type: Literal["contains", "starts_with", "exact"] = "contains"
    category: str
    from_transaction_id: int | None = None
    apply_to_review_rows: bool = True


class RuleToggleIn(BaseModel):
    enabled: bool


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    load_rulebook()  # fail at start-up, not on the first upload, if rules.yaml is broken

    setup_conn = storage.connect(settings.db_path)
    storage.migrate(setup_conn)
    setup_conn.close()

    app = FastAPI(title="Statement Categorizer", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    def db():
        conn = storage.connect(settings.db_path)
        try:
            yield conn
        finally:
            conn.close()

    @app.exception_handler(service.AppError)
    async def app_error(_: Request, exc: service.AppError):
        return JSONResponse(status_code=exc.status, content={"detail": exc.message})

    @app.get("/api/meta")
    def meta():
        book = load_rulebook()
        return {
            "categories": [{"name": n, "kind": k} for n, k in book.categories.items()],
            "ocr_available": ocr_available(),
            "max_upload_mb": settings.max_upload_mb,
            "built_in_rule_count": sum(1 for _ in book.all_rules()),
        }

    @app.post("/api/statements", status_code=201)
    async def upload(
        file: UploadFile = File(...),
        account_type: Literal["business", "mixed"] = Form("business"),
        currency: Literal["auto", "PKR", "USD"] = Form("auto"),
        date_format: Literal["auto", "day_first", "month_first"] = Form("auto"),
        conn=Depends(db),
    ):
        limit = settings.max_upload_mb * 1024 * 1024
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise service.AppError(f"The file is larger than {settings.max_upload_mb} MB.")
        return service.import_statement(
            conn, filename=file.filename or "statement", data=data,
            account_type=account_type, currency=currency, date_format=date_format,
        )

    @app.get("/api/statements")
    def statements(conn=Depends(db)):
        return [service.statement_to_dict(s) for s in storage.list_statements(conn)]

    @app.delete("/api/statements/{statement_id}", status_code=204)
    def delete_statement(statement_id: int, conn=Depends(db)):
        with conn:
            if not storage.delete_statement(conn, statement_id):
                raise service.NotFound("Statement not found.")

    @app.delete("/api/statements", status_code=204)
    def delete_everything(conn=Depends(db)):
        with conn:
            storage.delete_all(conn)

    @app.get("/api/transactions")
    def transactions(
        statement_id: int | None = None,
        status: Literal["auto", "needs_review", "user_corrected"] | None = None,
        conn=Depends(db),
    ):
        return [service.txn_to_dict(r) for r in storage.list_transactions(conn, statement_id, status)]

    @app.patch("/api/transactions/{txn_id}")
    def correct(txn_id: int, body: CorrectionIn, conn=Depends(db)):
        return service.correct_transaction(conn, txn_id, body.category)

    @app.get("/api/summary")
    def summary(statement_id: int | None = None, conn=Depends(db)):
        return service.summary(conn, statement_id)

    @app.get("/api/export.csv")
    def export(statement_id: int | None = Query(None), conn=Depends(db)):
        return Response(
            content=service.export_csv(conn, statement_id),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="categorized-transactions.csv"'},
        )

    @app.get("/api/rules")
    def rules(conn=Depends(db)):
        return service.list_rules(conn)

    @app.post("/api/rules/preview")
    def preview_rule(body: RuleIn, conn=Depends(db)):
        return service.preview_rule(conn, body.pattern, body.match_type, body.category)

    @app.post("/api/rules", status_code=201)
    def create_rule(body: RuleIn, conn=Depends(db)):
        return service.create_rule(
            conn, pattern=body.pattern, match_type=body.match_type, category=body.category,
            from_txn_id=body.from_transaction_id, apply=body.apply_to_review_rows,
        )

    @app.patch("/api/rules/{rule_id}")
    def toggle_rule(rule_id: int, body: RuleToggleIn, conn=Depends(db)):
        return service.set_rule_enabled(conn, rule_id, body.enabled)

    @app.delete("/api/rules/{rule_id}", status_code=204)
    def delete_rule(rule_id: int, conn=Depends(db)):
        service.delete_rule(conn, rule_id)

    return app


app = create_app()
