from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.settings import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    is_sqlite = url.startswith("sqlite")
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False} if is_sqlite else {})
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


def init_db(engine: Engine | None = None) -> None:
    """Create the tables if they do not exist.

    Fine for this scope. For production the next step is Alembic migrations, so schema
    changes are versioned and can be applied to an existing database.
    """
    from app import models  # noqa: F401  (registers the tables on Base)

    Base.metadata.create_all(engine or get_engine())


def get_db() -> Iterator[Session]:
    with sessionmaker(bind=get_engine(), expire_on_commit=False)() as session:
        yield session
