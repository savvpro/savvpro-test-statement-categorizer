from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.brain.classifier import Classifier
from app.brain.rules import RuleTable
from app.config import Settings
from app.main import create_app
from app.storage.user_rules import UserRuleStore

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample-data"


@pytest.fixture(scope="session")
def rule_table() -> RuleTable:
    return RuleTable.load()


@pytest.fixture
def classifier(rule_table: RuleTable) -> Classifier:
    return Classifier(rule_table)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Limits are generous so only the rate-limit tests ever trip them.
    return Settings(
        data_dir=tmp_path,
        rate_limit_uploads_per_minute=1000,
        rate_limit_requests_per_minute=10_000,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def user_rules(tmp_path: Path) -> UserRuleStore:
    return UserRuleStore(tmp_path / "rules.json")


def upload(client: TestClient, name: str, data: bytes, **form: str):
    return client.post("/api/statements", files={"file": (name, data)}, data=form)
