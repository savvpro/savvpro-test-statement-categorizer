"""LedgerLens FastAPI application entry point.

Registers Jinja2 templates, static files, API routes, and web page routes.
Run with: uvicorn app.main:app --reload (from the backend/ directory)
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings

# Import route modules
from app.api.routes import health, statements, transactions, categories, dashboard, rules, reports, reconciliation, export, backups
from app.web import routes as web_routes

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

settings = get_settings()

app = FastAPI(
    title="LedgerLens — Smart Statement Categorizer",
    description=(
        "Import CSV bank and credit card statements, categorize transactions "
        "with a custom Python rules engine, and review uncertain classifications."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ---------------------------------------------------------------------------
# Static files and Jinja2 templates
# ---------------------------------------------------------------------------

_BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=str(_BASE_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))

# Inject templates into web routes module
web_routes.set_templates(templates)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

# JSON API routers
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(rules.router)
app.include_router(reports.router)
app.include_router(reconciliation.router)
app.include_router(export.router)
app.include_router(backups.router)


# Server-rendered HTML page router
app.include_router(web_routes.router)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> Response:
    if request.url.path.startswith("/api/"):
        detail = getattr(exc, "detail", "Not Found")
        return JSONResponse(status_code=404, content={"detail": detail})
    return templates.TemplateResponse(
        request=request,
        name="errors/404.html",
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception) -> Response:
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return templates.TemplateResponse(
        request=request,
        name="errors/500.html",
        context={"detail": str(exc)},
        status_code=500,
    )


