"""slowapi limiter shared by upload routes. The limit string is set from Settings at startup."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.errors import problem_response

limiter = Limiter(key_func=get_remote_address, headers_enabled=False)
_state = {"limit": "30/minute"}


def current_limit() -> str:
    return _state["limit"]


def configure_rate_limit(app: FastAPI, limit: str) -> None:
    _state["limit"] = limit
    limiter.reset()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limited)


async def _rate_limited(request: Request, exc: Exception) -> JSONResponse:
    return problem_response(
        request, 429, "Too many requests", "Upload rate limit exceeded", code="RATE_LIMITED"
    )
