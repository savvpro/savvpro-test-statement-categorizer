import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app.brain.rules_loader import load_rules
from app.main import app
from app.schemas import Transaction


@pytest.fixture
def rules():
    return load_rules()


@pytest.fixture
def make_txn():
    counter = {"n": 1}

    def _make(description, amount, date="2026-10-01", currency="USD", row=None):
        counter["n"] += 1
        n = row or counter["n"]
        return Transaction(
            id=f"row-{n}",
            row=n,
            date=dt.date.fromisoformat(date),
            raw_description=description,
            description=description.upper(),
            amount=amount,
            currency=currency,
        )

    return _make


@pytest.fixture
def client():
    return TestClient(app)