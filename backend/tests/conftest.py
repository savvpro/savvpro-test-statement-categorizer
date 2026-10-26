from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from statement_categorizer.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path / "test.sqlite3", static_dir=tmp_path / "no-frontend")


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://localhost") as client:
        yield client


@pytest.fixture
def sample_bytes():
    return (Path(__file__).resolve().parents[2] / "samples" / "designer-bank.csv").read_bytes()


def upload(client, data: bytes, **options):
    return client.post("/api/statements", files={"file": ("statement.csv", data, "text/csv")}, data=options)
