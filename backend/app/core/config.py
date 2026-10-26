"""Application configuration and database connection validation.

Loads environment variables from local .env using python-dotenv, validates
MySQL-only requirements, and masks credentials in logs and representations.
"""

import os
from pathlib import Path
import re
from typing import Optional
from dotenv import load_dotenv

# Load .env from backend directory or project root if present
_backend_dir = Path(__file__).resolve().parent.parent.parent
_env_path = _backend_dir / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()


def mask_database_url(url: Optional[str]) -> str:
    """Mask password credentials in a database URL for safe logging and errors.

    Example:
        'mysql+pymysql://user:secret123@localhost:3306/db'
        -> 'mysql+pymysql://user:***@localhost:3306/db'
    """
    if not url:
        return "Not Configured"
    # Match scheme://user:password@host
    return re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1***\3", url)


def validate_mysql_url(url: str, is_test_db: bool = False) -> str:
    """Validate that the given URL specifies a supported MySQL connection.

    Rejects SQLite or any other non-MySQL dialect.
    """
    if not url or not url.strip():
        raise ValueError("Database URL cannot be empty.")

    cleaned = url.strip()
    lower_cleaned = cleaned.lower()

    if lower_cleaned.startswith("sqlite"):
        raise ValueError(
            "SQLite is strictly prohibited for LedgerLens. "
            "MySQL 8.0+ is the only supported database."
        )

    if not (lower_cleaned.startswith("mysql+pymysql://") or lower_cleaned.startswith("mysql://")):
        raise ValueError(
            f"Unsupported database scheme. Only 'mysql+pymysql://' is supported. "
            f"Received: {mask_database_url(cleaned)}"
        )

    if is_test_db:
        # Enforce that test database URL explicitly targets a test database name
        # to prevent accidental destructive operations on production or development databases.
        db_name = cleaned.split("/")[-1].split("?")[0].lower()
        if "test" not in db_name:
            raise ValueError(
                f"Dedicated test database URL must contain 'test' in its database name. "
                f"Received database: '{db_name}'. Target: {mask_database_url(cleaned)}"
            )

    return cleaned


class Settings:
    """Centralized application settings."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "LedgerLens")
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.app_debug: bool = os.getenv("APP_DEBUG", "true").lower() in {"true", "1", "yes"}
        self.max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

        # Database URLs
        self._database_url: Optional[str] = os.getenv("DATABASE_URL")
        self._test_database_url: Optional[str] = os.getenv("TEST_DATABASE_URL")

        # Phase 8: Backup and Data Management settings
        default_backup_dir = str(_backend_dir / "backups")
        self.backup_directory: Path = Path(os.getenv("BACKUP_DIRECTORY", default_backup_dir)).resolve()
        self.backup_retention_days: int = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self.backup_max_count: int = int(os.getenv("BACKUP_MAX_COUNT", "20"))
        self.auto_backup_enabled: bool = os.getenv("AUTO_BACKUP_ENABLED", "false").lower() in {"true", "1", "yes"}

    def get_backup_directory(self) -> Path:
        """Return the backup directory Path, ensuring it exists."""
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        return self.backup_directory

    @property
    def database_url(self) -> Optional[str]:
        """Return the raw configured DATABASE_URL without validation."""
        return self._database_url

    @property
    def test_database_url(self) -> Optional[str]:
        """Return the raw configured TEST_DATABASE_URL without validation."""
        return self._test_database_url

    def get_database_url(self) -> str:
        """Validate and return the required application DATABASE_URL.

        Raises ValueError if unconfigured or not a valid MySQL connection.
        """
        if not self._database_url:
            raise ValueError(
                "DATABASE_URL environment variable is not configured. "
                "Please configure a valid MySQL connection string in .env "
                "(e.g., 'mysql+pymysql://user:pass@localhost:3306/ledgerlens_db')."
            )
        return validate_mysql_url(self._database_url, is_test_db=False)

    def get_test_database_url(self) -> str:
        """Validate and return the dedicated test database URL.

        Raises ValueError if unconfigured or not pointing to a dedicated test DB.
        """
        if not self._test_database_url:
            raise ValueError(
                "TEST_DATABASE_URL environment variable is not configured. "
                "Integration tests require a dedicated MySQL test database "
                "(e.g., 'mysql+pymysql://ledgerlens_test:pass@localhost:3306/ledgerlens_test')."
            )
        return validate_mysql_url(self._test_database_url, is_test_db=True)

    @property
    def masked_database_url(self) -> str:
        """Safe masked representation of DATABASE_URL for logs."""
        return mask_database_url(self._database_url)

    @property
    def masked_test_database_url(self) -> str:
        """Safe masked representation of TEST_DATABASE_URL for logs."""
        return mask_database_url(self._test_database_url)

    def __repr__(self) -> str:
        return (
            f"Settings(app_name={self.app_name!r}, app_env={self.app_env!r}, "
            f"database_url={self.masked_database_url!r}, "
            f"test_database_url={self.masked_test_database_url!r})"
        )


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Return singleton Settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
