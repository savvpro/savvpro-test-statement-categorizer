from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import REPO_DIR, Settings
from app.db import Database
from app.main import create_app
from app.services import StatementService

SAMPLES = REPO_DIR / "samples"


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def service(db: Database) -> StatementService:
    return StatementService(db)


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "api.db",
        samples_dir=SAMPLES,
        cors_origins=["http://localhost:5173"],
        max_upload_bytes=64 * 1024,
        review_threshold=0.75,
    )
    with TestClient(create_app(settings)) as c:
        yield c


def csv_bytes(*lines: str) -> bytes:
    return ("\n".join(lines) + "\n").encode()
