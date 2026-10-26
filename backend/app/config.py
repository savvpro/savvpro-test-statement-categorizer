from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


def _csv_env(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    database_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("DRIVELEDGER_DB_PATH", str(BACKEND_DIR / "data" / "driveledger.db"))
        )
    )
    samples_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("DRIVELEDGER_SAMPLES_DIR", str(REPO_DIR / "samples"))
        )
    )
    cors_origins: list[str] = field(
        default_factory=lambda: _csv_env(
            "DRIVELEDGER_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )
    )
    max_upload_bytes: int = field(
        default_factory=lambda: int(
            float(os.getenv("DRIVELEDGER_MAX_UPLOAD_MB", "5")) * 1024 * 1024
        )
    )
    review_threshold: float = field(
        default_factory=lambda: float(os.getenv("DRIVELEDGER_REVIEW_THRESHOLD", "0.75"))
    )
