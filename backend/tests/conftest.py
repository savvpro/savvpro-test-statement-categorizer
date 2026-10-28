from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Every test gets its own empty SQLite file."""
    monkeypatch.setenv("CATEGORIZER_DB", str(tmp_path / "test.db"))


@pytest.fixture
def sample():
    return lambda name: (SAMPLES / name).read_bytes()
