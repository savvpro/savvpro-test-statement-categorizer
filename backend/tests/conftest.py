from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.core.config import Settings
from app.main import create_app
from tests.factories import fake_categorize

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        env="test",
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        rate_limit="1000/minute",
        auto_create_tables=True,
        rules_dir=RULES_DIR,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """App wired to a deterministic fake brain: tests the plumbing, not the rules."""
    with TestClient(create_app(settings, categorize=fake_categorize)) as c:
        yield c


@pytest.fixture
def real_client(settings: Settings) -> Iterator[TestClient]:
    """App wired to the real brain."""
    with TestClient(create_app(settings)) as c:
        yield c


def upload(
    client: TestClient,
    content: bytes | str,
    name: str = "jan.csv",
    account_type: str = "checking",
) -> Response:
    data = content.encode() if isinstance(content, str) else content
    return client.post(
        "/api/v1/statements",
        files={"file": (name, data, "application/octet-stream")},
        data={"account_type": account_type},
    )
