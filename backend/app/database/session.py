"""Database engine and session management.

Provides SQLAlchemy 2.x session factories, MySQL connection pooling,
and transactional context managers with explicit rollback handling.
"""

from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def create_db_engine(database_url: str, echo: bool = False) -> Engine:
    """Create a configured SQLAlchemy 2.x Engine for MySQL with connection pooling."""
    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,      # Automatically verify connection liveness before checkout
        pool_recycle=3600,       # Recycle connections older than 1 hour (common MySQL timeout defense)
        pool_size=10,
        max_overflow=20,
    )


_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None


def get_engine() -> Engine:
    """Get or initialize the application-wide database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.get_database_url()
        _engine = create_db_engine(db_url, echo=settings.app_debug)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get or initialize the application-wide sessionmaker."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


@contextmanager
def get_db(session_override: Optional[Session] = None) -> Generator[Session, None, None]:
    """Context manager providing a transactional database session.

    If an existing session is passed via session_override, it yields that session
    without committing or closing it (preserving caller ownership).
    Otherwise, creates a new session, commits on successful block exit,
    rolls back on exception, and closes on exit.
    """
    if session_override is not None:
        yield session_override
        return

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


def check_database_connection(engine: Optional[Engine] = None) -> bool:
    """Check if the target MySQL database is reachable."""
    target_engine = engine or get_engine()
    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
