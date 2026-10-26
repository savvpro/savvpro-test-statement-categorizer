"""Settings from environment variables (see .env.example). No secrets live in code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SAMPLE_DATA_DIR = Path(
    os.getenv("SAMPLE_DATA_DIR", Path(__file__).resolve().parents[2] / "sample_data")
)


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: list[str]
    max_upload_bytes: int


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/ledgerlite.db"),
        cors_origins=[
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if origin.strip()
        ],
        max_upload_bytes=int(float(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024),
    )
