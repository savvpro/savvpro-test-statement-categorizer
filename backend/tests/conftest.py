"""Shared fixtures."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

SAMPLES = BACKEND_DIR / "app" / "data" / "samples"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def designer_csv() -> Path:
    return SAMPLES / "sample_statement_designer.csv"


@pytest.fixture()
def messy_csv() -> Path:
    return SAMPLES / "sample_statement_messy.csv"
