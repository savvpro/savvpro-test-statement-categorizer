"""Exercise the byte limit without depending on Content-Length or multipart parsing."""

import asyncio

from statement_categorizer.main import RequestBoundary
from statement_categorizer.parser import MAX_FILE_BYTES


def test_chunked_body_limit_before_app_is_called():
    reached_app = False
    sent = []

    async def app(scope, receive, send):
        nonlocal reached_app
        reached_app = True

    messages = iter(
        [
            {"type": "http.request", "body": b"x" * MAX_FILE_BYTES, "more_body": True},
            {"type": "http.request", "body": b"x" * (64 * 1024 + 1), "more_body": False},
        ]
    )

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    boundary = RequestBoundary(app, set())
    asyncio.run(boundary({"type": "http", "method": "POST", "headers": []}, receive, send))
    assert not reached_app
    assert sent[0]["status"] == 413


def test_disconnected_upload_never_enters_the_app():
    reached_app = False

    async def app(scope, receive, send):
        nonlocal reached_app
        reached_app = True

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        raise AssertionError("No response can be sent after the client disconnected")

    asyncio.run(RequestBoundary(app, set())({"type": "http", "method": "POST", "headers": []}, receive, send))
    assert not reached_app
