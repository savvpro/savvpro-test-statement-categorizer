import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "data" / "rules.json"

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
BASE_CURRENCY = "USD"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")