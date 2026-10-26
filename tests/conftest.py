import pytest


@pytest.fixture
def anyio_backend():
    """The API uses asyncio; do not require the optional Trio dependency."""
    return "asyncio"
