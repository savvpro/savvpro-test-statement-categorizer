import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SORTEDHISAB_DB", str(tmp_path / "test.sqlite3"))
    with TestClient(app) as session:
        yield session
