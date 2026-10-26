"""Application configuration via pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # App
    app_title: str = "Ledgerline API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./ledgerline.db"

    # CORS – comma-separated origins
    cors_origins: str = "http://localhost:3000"

    # Brain
    review_threshold: float = 0.75
    review_margin: float = 0.15
    equipment_demin_cents: int = 250_000  # $2,500.00

    # Upload
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB
    import_draft_ttl_minutes: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
