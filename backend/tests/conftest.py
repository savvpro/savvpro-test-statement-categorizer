import os

# Backstop: anything that reaches for the default engine gets a throwaway in-memory DB,
# never data/app.db. Must run before any `app` import builds the module-level engine.
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import create_db_engine, get_db, init_db
from app.main import create_app


@pytest.fixture
def engine() -> Iterator[Engine]:
    # StaticPool keeps one connection so every session sees the same in-memory database.
    test_engine = create_db_engine("sqlite://", poolclass=StaticPool)
    init_db(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def client(engine: Engine, session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app(engine=engine)

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
