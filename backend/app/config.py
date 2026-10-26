import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _origins() -> list[str]:
    raw = os.getenv("APP_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


def _db_path() -> Path:
    return Path(os.getenv("APP_DB_PATH", BACKEND_DIR / "data" / "categorizer.db"))


@dataclass
class Settings:
    db_path: Path = field(default_factory=_db_path)
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("APP_MAX_UPLOAD_MB", "10")))
    allowed_origins: list[str] = field(default_factory=_origins)
