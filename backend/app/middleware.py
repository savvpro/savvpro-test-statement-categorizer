"""ASGI middleware: request size cap, rate limiting and safe default headers."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Multipart framing adds a little to the file itself.
_MULTIPART_OVERHEAD = 64 * 1024


def error_response(
    status: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        {"detail": {"code": code, "message": message}}, status_code=status, headers=headers
    )


class _BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    """Reject oversized bodies early, whether or not the client declares a length."""

    def __init__(self, app: ASGIApp, max_body_bytes: int):
        self.app = app
        self.limit = max_body_bytes + _MULTIPART_OVERHEAD
        self._message = f"The upload is larger than {max_body_bytes // (1024 * 1024)} MB."

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                too_big = int(declared) > self.limit
            except ValueError:
                too_big = False
            if too_big:
                await error_response(413, "file_too_large", self._message)(scope, receive, send)
                return

        received = 0
        started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    raise _BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if started:
                raise
            await error_response(413, "file_too_large", self._message)(scope, receive, send)


class SlidingWindowLimiter:
    """Allow `limit` hits per `window` seconds per key. Thread-safe, memory bounded."""

    def __init__(
        self,
        limit: int,
        window: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ):
        self.limit = limit
        self.window = window
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> float:
        """Return 0 if allowed (and count the hit), else seconds until the next slot opens."""
        now = self._clock()
        with self._lock:
            if len(self._hits) >= self._max_keys:
                self._prune(now)
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(self.window - (now - hits[0]), 0.001)
            hits.append(now)
            return 0.0

    def _prune(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]:
            del self._hits[key]


class RateLimitMiddleware:
    """Per-client limits: a tight one for uploads, a looser one for everything else."""

    EXEMPT_PATHS = {"/api/health"}

    def __init__(
        self,
        app: ASGIApp,
        *,
        uploads_per_minute: int,
        requests_per_minute: int,
        trust_proxy_headers: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.app = app
        self._uploads = SlidingWindowLimiter(uploads_per_minute, clock=clock)
        self._general = SlidingWindowLimiter(requests_per_minute, clock=clock)
        self._trust_proxy = trust_proxy_headers

    def _client(self, scope: Scope) -> str:
        if self._trust_proxy:
            for name, value in scope["headers"]:
                if name == b"x-forwarded-for":
                    return value.decode("latin-1").split(",")[0].strip() or "unknown"
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        if path in self.EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        client = self._client(scope)
        is_upload = scope["method"] == "POST" and path.rstrip("/") == "/api/statements"
        wait = self._general.check(client)
        if wait == 0.0 and is_upload:
            wait = self._uploads.check(client)
        if wait > 0.0:
            retry = str(max(1, math.ceil(wait)))
            kind = "uploads" if is_upload else "requests"
            response = error_response(
                429,
                "rate_limited",
                f"Too many {kind}. Try again in {retry} seconds.",
                headers={"Retry-After": retry},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list[Any] = list(message.get("headers", []))
                existing = {k.lower() for k, _ in headers}
                for name, value in (
                    (b"x-content-type-options", b"nosniff"),
                    (b"cache-control", b"no-store"),
                    (b"referrer-policy", b"no-referrer"),
                ):
                    if name not in existing:
                        headers.append((name, value))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, with_headers)
