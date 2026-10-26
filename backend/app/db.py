"""Database engine and session management for SQLite."""

from __future__ import annotations

# pyrefly: ignore[missing-import]
from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL, DB_DIR

DB_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # SQLite only
)


def init_db() -> None:
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency – yields a DB session."""
    with Session(engine) as session:
        yield session
