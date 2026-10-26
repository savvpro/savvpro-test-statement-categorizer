"""Unit tests for configuration, environment loading, and MySQL URL validation."""

import pytest
from app.core.config import Settings, mask_database_url, validate_mysql_url


def test_mask_database_url_masks_password():
    """Verify passwords are masked and never exposed in logs or strings."""
    url = "mysql+pymysql://test_user:superSecretPassword123@localhost:3306/ledgerlens_db"
    masked = mask_database_url(url)

    assert "superSecretPassword123" not in masked
    assert "test_user:***@localhost:3306" in masked


def test_mask_database_url_handles_none_and_empty():
    """Verify None or empty URLs produce safe fallback text."""
    assert mask_database_url(None) == "Not Configured"
    assert mask_database_url("") == "Not Configured"


def test_validate_mysql_url_accepts_valid_mysql():
    """Verify standard MySQL connection strings are accepted."""
    valid_url = "mysql+pymysql://user:pass@localhost:3306/ledgerlens_db"
    assert validate_mysql_url(valid_url) == valid_url


def test_validate_mysql_url_strictly_rejects_sqlite():
    """Verify SQLite is strictly prohibited and raises a clear error."""
    with pytest.raises(ValueError) as exc:
        validate_mysql_url("sqlite:///ledgerlens.db")
    assert "SQLite is strictly prohibited" in str(exc.value)


def test_validate_mysql_url_rejects_non_mysql_dialects():
    """Verify PostgreSQL, Oracle, and other non-MySQL dialects are rejected."""
    with pytest.raises(ValueError) as exc:
        validate_mysql_url("postgresql+psycopg2://user:pass@localhost/db")
    assert "Only 'mysql+pymysql://' is supported" in str(exc.value)


def test_test_database_url_enforces_test_db_name():
    """Verify test database URLs must contain 'test' to prevent production pollution."""
    # Valid test URL
    valid_test = "mysql+pymysql://user:pass@localhost:3306/ledgerlens_test"
    assert validate_mysql_url(valid_test, is_test_db=True) == valid_test

    # Non-test URL rejected for test context
    with pytest.raises(ValueError) as exc:
        validate_mysql_url("mysql+pymysql://user:pass@localhost:3306/production_db", is_test_db=True)
    assert "Dedicated test database URL must contain 'test'" in str(exc.value)


def test_missing_database_url_raises_clear_error(monkeypatch):
    """Verify calling get_database_url() when unconfigured raises descriptive ValueError."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings()
    settings._database_url = None

    with pytest.raises(ValueError) as exc:
        settings.get_database_url()
    assert "DATABASE_URL environment variable is not configured" in str(exc.value)
