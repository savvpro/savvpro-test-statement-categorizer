"""Commit semantics, concurrent-duplicate race and migration tests."""

import os
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.repositories import StatementRepo
from app.main import create_app
from tests.conftest import upload
from tests.factories import bank_csv, fake_categorize


def test_concurrent_identical_upload_integrity_error_is_409(client: TestClient) -> None:
    """Lose the race: the pre-check misses, the unique constraint catches it."""
    first = upload(client, bank_csv()).json()
    real_find = StatementRepo.find_by_sha
    calls = {"n": 0}

    def flaky(self: StatementRepo, sha: str) -> Any:
        calls["n"] += 1
        return None if calls["n"] == 1 else real_find(self, sha)

    with patch.object(StatementRepo, "find_by_sha", flaky):
        r = upload(client, bank_csv(), name="again.csv")
    assert r.status_code == 409
    assert r.json()["existing_id"] == first["id"]
    assert len(client.get("/api/v1/statements").json()) == 1


def test_commit_failure_is_problem_json_with_headers_and_rolls_back(settings: Settings) -> None:
    app = create_app(settings, categorize=fake_categorize)
    with TestClient(app, raise_server_exceptions=False) as c:
        with patch.object(Session, "commit", side_effect=RuntimeError("disk full")):
            r = upload(c, bank_csv())
        assert r.status_code == 500
        assert r.headers["content-type"].startswith("application/problem+json")
        assert r.headers["x-content-type-options"] == "nosniff"
        assert "content-security-policy" in r.headers
        assert r.headers["x-request-id"]
        assert c.get("/api/v1/statements").json() == []


def test_migration_0002_up_down(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    db = tmp_path / "m.db"
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    os.environ["APP_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    get_settings.cache_clear()

    def ddl() -> str:
        con = sqlite3.connect(db)
        try:
            return str(
                con.execute("select sql from sqlite_master where name='statements'").fetchone()[0]
            )
        finally:
            con.close()

    try:
        command.upgrade(cfg, "head")
        assert "uq_statements_file_sha256" in ddl()
        command.downgrade(cfg, "0001")
        assert "uq_statements_file_sha256" not in ddl()
    finally:
        os.environ.pop("APP_DATABASE_URL", None)
        get_settings.cache_clear()


@pytest.mark.parametrize("path", ["/api/v1/statements/nope", "/api/v1/statements/nope/summary"])
def test_404_is_problem_json(client: TestClient, path: str) -> None:
    r = client.get(path)
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"
