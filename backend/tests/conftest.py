from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.categorization.factory import build_engine
from app.categorization.rulebook import RuleBook
from app.config import Settings
from app.domain.models import RawTransaction
from app.learning.repository import InMemoryMerchantRuleRepository
from app.main import create_app


@pytest.fixture
def repository():
    return InMemoryMerchantRuleRepository()


@pytest.fixture
def engine(repository):
    return build_engine(Settings(), RuleBook.load(), repository)


@pytest.fixture
def client(repository):
    return TestClient(create_app(Settings(), rule_repository=repository))


def make_tx(row, description, amount, day=1, month=3):
    return RawTransaction(row=row, date=date(2026, month, day), description=description, amount=Decimal(amount))
