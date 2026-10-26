import os
import tempfile

# The app's own database must never be touched by tests: point it at a throwaway
# directory before anything reads the settings.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp(prefix='stmt-tests-')}/app.db"

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.db import Base, get_db, make_engine  # noqa: E402
from app.main import app  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


@pytest.fixture
def session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


def upload(client: TestClient, name: str, content: bytes | None = None):
    """Upload a sample file (or the given bytes under that name)."""
    data = content if content is not None else (SAMPLE_DIR / name).read_bytes()
    return client.post("/api/statements", files={"file": (name, data, "text/csv")})
