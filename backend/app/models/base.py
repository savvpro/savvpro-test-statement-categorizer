"""SQLAlchemy declarative base definition."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Central declarative base for all LedgerLens ORM models."""

    pass
