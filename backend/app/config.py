"""Runtime configuration, read once from the environment (12-factor style)."""
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Tuple

DEFAULT_RULES_STORE = Path(__file__).resolve().parents[1] / "var" / "merchant_rules.json"


@dataclass(frozen=True)
class Settings:
    cors_origins: Tuple[str, ...] = ("http://localhost:5173",)
    max_upload_bytes: int = 5 * 1024 * 1024
    max_rows: int = 10_000
    confidence_threshold: float = 0.7
    ambiguity_margin: float = 0.2
    large_amount: Decimal = Decimal("1000")
    rules_store_path: str = str(DEFAULT_RULES_STORE)

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            cors_origins=tuple(os.getenv("CORS_ORIGINS", ",".join(defaults.cors_origins)).split(",")),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", defaults.max_upload_bytes)),
            max_rows=int(os.getenv("MAX_ROWS", defaults.max_rows)),
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", defaults.confidence_threshold)),
            ambiguity_margin=float(os.getenv("AMBIGUITY_MARGIN", defaults.ambiguity_margin)),
            large_amount=Decimal(os.getenv("LARGE_AMOUNT", defaults.large_amount)),
            rules_store_path=os.getenv("RULES_STORE_PATH", defaults.rules_store_path),
        )
