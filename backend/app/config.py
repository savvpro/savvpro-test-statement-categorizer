from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SC_", env_file=".env", extra="ignore")

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    max_upload_bytes: int = 5 * 1024 * 1024
    max_rows: int = 5000
    max_statements: int = 200  # oldest statements are dropped beyond this (in-memory store)
    currency: str = "PKR"
    rules_path: Path | None = None  # defaults to app/brain/rules.json


@lru_cache
def get_settings() -> Settings:
    return Settings()
