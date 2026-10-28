"""Liveness and readiness."""

import logging

from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from app.api.schemas import HealthOut

log = logging.getLogger("app.health")
router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthOut)
def healthz() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/readyz", response_model=HealthOut, responses={503: {"model": HealthOut}})
def readyz(request: Request, response: Response) -> HealthOut:
    try:
        with request.app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
        ready = getattr(request.app.state, "ruleset", None) is not None
    except Exception:
        log.warning("readyz: database check failed", exc_info=True)
        ready = False
    if not ready:
        response.status_code = 503
        return HealthOut(status="not_ready")
    return HealthOut(status="ready")
