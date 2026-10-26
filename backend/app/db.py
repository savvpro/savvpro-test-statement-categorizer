"""SQLite engine and session dependency."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

_engine: Engine | None = None


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        if url in ("sqlite://", "sqlite:///:memory:"):
            return create_engine(
                url, connect_args={"check_same_thread": False}, poolclass=StaticPool
            )
        path = url.removeprefix("sqlite:///")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)  # pragma: no cover - other databases are not used yet


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
    return _engine


def set_engine(engine: Engine) -> None:
    """Swap the engine (used by tests)."""
    global _engine
    _engine = engine


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
