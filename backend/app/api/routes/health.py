"""Health check JSON API endpoint."""

from fastapi import APIRouter
from app.database.session import check_database_connection

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", summary="Health check")
def health_check() -> dict:
    """Return application health and database connectivity status."""
    db_ok = check_database_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
    }
