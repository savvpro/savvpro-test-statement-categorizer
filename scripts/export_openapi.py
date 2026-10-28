"""Write backend/openapi.json from the FastAPI app (no server needed)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> None:
    app = create_app(Settings(env="development", database_url="sqlite://"))
    out = ROOT / "backend" / "openapi.json"
    out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
