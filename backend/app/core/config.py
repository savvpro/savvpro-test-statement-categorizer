"""Application settings (env prefix APP_)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    env: str = "production"  # dev/test opt in via APP_ENV
    database_url: str = "sqlite:///./data/app.db"
    cors_origins: str = "http://localhost:3000"
    max_upload_bytes: int = 5_242_880
    max_rows: int = 20_000
    auto_threshold: float = 0.85
    margin_threshold: float = 0.20
    de_minimis_cents: int = 250_000
    contractor_1099_cents: int = 60_000
    fuzzy_min_ratio: int = 88
    rate_limit: str = "30/minute"
    log_level: str = "INFO"
    rules_dir: Path = Path("./rules")
    # Dev/test convenience; production uses `alembic upgrade head`.
    auto_create_tables: bool = False

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
