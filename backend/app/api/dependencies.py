"""FastAPI dependency injection helpers."""

from typing import Generator
from sqlalchemy.orm import Session
from app.database.session import get_session_factory


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a database session and close after request."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
