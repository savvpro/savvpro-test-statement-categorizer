from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.brain.categorizer import Categorizer
from app.config import Settings
from app.main import create_app

SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "driver_statement.csv"


@pytest.fixture(scope="session")
def brain() -> Categorizer:
    return Categorizer()


@pytest.fixture
def sample_bytes() -> bytes:
    return SAMPLE_CSV.read_bytes()


@pytest.fixture
def client() -> TestClient:
    """A fresh app (and so a fresh in-memory store) for every test."""
    return TestClient(create_app(Settings(_env_file=None)))


def upload(client: TestClient, content: bytes, name: str = "statement.csv", **params):
    return client.post(
        "/api/statements", files={"file": (name, content, "text/csv")}, params=params
    )


def by_row(statement: dict) -> dict[int, dict]:
    return {t["row"]: t for t in statement["transactions"]}
