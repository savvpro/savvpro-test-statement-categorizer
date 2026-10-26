"""Runtime settings, read from SC_* environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

ACCEPTED_EXTENSIONS = (
    ".csv",
    ".tsv",
    ".txt",
    ".xlsx",
    ".ofx",
    ".qfx",
    ".pdf",
    ".xml",
    ".sta",
    ".mt940",
    ".940",
    ".dat",
)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    return value


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    max_upload_mb: int = 5
    max_rows: int = 5000
    max_pdf_pages: int = 40
    review_threshold: float = 0.75
    default_currency: str = "USD"
    large_amount: Decimal = Decimal("1000")
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    rate_limit_uploads_per_minute: int = 10
    rate_limit_requests_per_minute: int = 120
    trust_proxy_headers: bool = False
    data_dir: Path = field(default_factory=lambda: Path("var"))
    max_stored_statements: int = 200

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def user_rules_path(self) -> Path:
        return self.data_dir / "user_rules.json"

    @classmethod
    def from_env(cls) -> Settings:
        origins = os.environ.get("SC_CORS_ORIGINS", "http://localhost:5173")
        return cls(
            max_upload_mb=_env_int("SC_MAX_UPLOAD_MB", 5),
            max_rows=_env_int("SC_MAX_ROWS", 5000),
            max_pdf_pages=_env_int("SC_MAX_PDF_PAGES", 40),
            review_threshold=_env_float("SC_REVIEW_THRESHOLD", 0.75),
            default_currency=os.environ.get("SC_DEFAULT_CURRENCY", "USD").upper(),
            large_amount=Decimal(str(_env_float("SC_LARGE_AMOUNT", 1000))),
            cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
            rate_limit_uploads_per_minute=_env_int("SC_RATE_LIMIT_UPLOADS_PER_MINUTE", 10),
            rate_limit_requests_per_minute=_env_int("SC_RATE_LIMIT_REQUESTS_PER_MINUTE", 120),
            trust_proxy_headers=_env_bool("SC_TRUST_PROXY_HEADERS", False),
            data_dir=Path(os.environ.get("SC_DATA_DIR", "var")),
            max_stored_statements=_env_int("SC_MAX_STORED_STATEMENTS", 200),
        )
