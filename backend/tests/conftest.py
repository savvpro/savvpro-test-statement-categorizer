from pathlib import Path

import pytest

from app.engine import categorize_all
from app.parser import parse_csv

SAMPLE = Path(__file__).parents[2] / "sample_statement_pkr.csv"


@pytest.fixture(scope="session")
def sample_text() -> str:
    return SAMPLE.read_text(encoding="utf-8-sig")


@pytest.fixture(scope="session")
def rows(sample_text):
    """Categorized sample rows keyed by id, plus a lookup by description."""
    return categorize_all(parse_csv(sample_text).transactions)


@pytest.fixture(scope="session")
def by_desc(rows):
    """First row for each raw description (some descriptions repeat in the sample)."""
    found = {}
    for tx in rows:
        found.setdefault(tx.description, tx)
    return found
