import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LEDGERLENS_DB", str(tmp_path / "test.db"))
    with TestClient(app) as session:
        yield session
