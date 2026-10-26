"""Alembic environment configuration."""

import logging
from logging.config import fileConfig
import os
import sys
from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import get_settings, mask_database_url
from app.models.base import Base
# Import all models so Alembic registers all tables with Base.metadata
import app.models  # noqa: F401

config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Set target metadata to application declarative base
target_metadata = Base.metadata


def get_target_url() -> str:
    """Retrieve database URL from application settings or environment."""
    # Check if URL was explicitly passed in alembic config
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url and ini_url.strip():
        return ini_url

    settings = get_settings()
    try:
        return settings.get_database_url()
    except ValueError as exc:
        logger.error(
            "Database URL could not be resolved from configuration: %s. "
            "Ensure DATABASE_URL is defined in .env.",
            exc,
        )
        raise


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without opening a live database connection.
    """
    url = get_target_url()
    logger.info("Running migrations offline for: %s", mask_database_url(url))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    url = get_target_url()
    logger.info("Connecting to MySQL for migrations: %s", mask_database_url(url))

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
