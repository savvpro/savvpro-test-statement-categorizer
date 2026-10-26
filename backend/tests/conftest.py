import os
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

# app.main builds a default app on import; keep it away from the real data folder.
os.environ.setdefault("APP_DB_PATH", str(Path(tempfile.mkdtemp()) / "import-time.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app.categorizer.engine import Engine, PastTxn, Txn  # noqa: E402
from app.categorizer.rules import Rule, load_rulebook  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "sample_data"


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(Settings(db_path=tmp_path / "test.db")))


@pytest.fixture
def upload(client):
    """Upload bytes or a sample file name and return the response."""
    def _upload(content, name="statement.csv", **form):
        if isinstance(content, str) and (SAMPLES / content).exists():
            name, content = content, (SAMPLES / content).read_bytes()
        if isinstance(content, str):
            content = content.encode()
        return client.post("/api/statements", files={"file": (name, content)}, data=form)
    return _upload


def txn(description, amount, when="2026-03-10", currency="PKR"):
    return Txn(date.fromisoformat(when), description, Decimal(amount), currency)


def engine(account_type="business", history=None, user_rules=None):
    book = load_rulebook()
    if user_rules:
        book = book.with_user_rules(user_rules)
    return Engine(book, account_type, history or [])


def past(id, description_rule, amount, when, currency="PKR", category="Software & Subscriptions"):
    return PastTxn(id, date.fromisoformat(when), Decimal(amount), currency, description_rule, category)


def user(id, pattern, category, match="contains"):
    return Rule(id=f"USER-{id}", pattern=pattern, match=match, category=category, source="user")
