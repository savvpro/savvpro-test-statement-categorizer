from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from app import db
from app.main import create_app

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


@pytest.fixture()
def sample_dir() -> Path:
    return SAMPLE_DIR


@pytest.fixture()
def engine():
    engine = db.make_engine("sqlite://")
    db.set_engine(engine)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(engine):
    with TestClient(create_app()) as test_client:
        yield test_client
