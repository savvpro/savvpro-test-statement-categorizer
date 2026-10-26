"""Start the built frontend and API together, bound to this computer only."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    if not (ROOT / "frontend" / "dist" / "index.html").exists():
        sys.exit("Frontend not built. Run npm ci and npm run build inside frontend first.")
    import uvicorn

    print("Ledgerly is starting at http://127.0.0.1:8000. Press Ctrl+C to stop.")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000)
