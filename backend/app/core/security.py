"""Upload validation, filename sanitising, HTTP hardening middleware, CSV escaping."""

import logging
import re
import time
import uuid
from pathlib import PurePath
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import UploadTooLarge
from app.core.headers import security_headers
from app.core.logging import request_id_var

access_log = logging.getLogger("app.access")

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_CSV_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")
MULTIPART_OVERHEAD = 64 * 1024


def sanitize_filename(name: str | None) -> str:
    """Basename only, no control characters, max 255 chars. Display label only."""
    raw = (name or "").replace("\\", "/")
    base = PurePath(raw).name
    base = _CONTROL_RE.sub("", base).strip()
    if base in {"", ".", ".."}:
        return "upload"
    return base[:255]


def safe_download_stem(filename: str) -> str:
    stem = PurePath(filename).stem
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.")
    return cleaned[:80] or "statement"


async def read_upload_limited(upload: Any, max_bytes: int) -> bytes:
    """Read an UploadFile in chunks, aborting as soon as the limit is exceeded."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise UploadTooLarge(f"File exceeds the {max_bytes} byte limit")
        chunks.append(chunk)
    return b"".join(chunks)


def csv_escape(value: str) -> str:
    """Neutralise spreadsheet formula injection (OWASP CSV injection)."""
    stripped = value.lstrip()
    if stripped and stripped[0] in _CSV_TRIGGERS:
        return "'" + value
    if value and value[0] in _CSV_TRIGGERS:
        return "'" + value
    return value


class RequestIdMiddleware:
    """Outermost: assigns/validates X-Request-ID and writes one JSON access-log line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = MutableHeaders(scope=scope).get("x-request-id")
        rid = incoming if incoming and _REQUEST_ID_RE.match(incoming) else str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = rid
        request_id_var.set(rid)
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = rid
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            access_log.info(
                "request",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_holder["status"],
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, relax_csp_paths: tuple[str, ...] = ()) -> None:
        self.app = app
        self.relax = relax_csp_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        relaxed = scope.get("path", "").startswith(self.relax) if self.relax else False

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                h = MutableHeaders(scope=message)
                for name, value in security_headers(relaxed=relaxed).items():
                    h[name] = value
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodySizeLimitMiddleware:
    """Rejects oversize bodies by Content-Length and by counting streamed bytes."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.limit = max_bytes + MULTIPART_OVERHEAD

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = MutableHeaders(scope=scope).get("content-length")
        if length is not None and length.isdigit() and int(length) > self.limit:
            await self._reject(scope, receive, send)
            return
        received = 0

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    raise UploadTooLarge("Request body exceeds the upload limit")
            return message

        await self.app(scope, counting_receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        from starlette.requests import Request

        from app.core.errors import problem_response

        request = Request(scope, receive)
        response = problem_response(
            request,
            413,
            "Upload too large",
            "Request body exceeds the upload limit",
            code="UPLOAD_TOO_LARGE",
        )
        await response(scope, receive, send)
