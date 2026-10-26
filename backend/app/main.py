"""FastAPI entrypoint.

Dev mode:  uvicorn app.main:app --reload  (frontend runs via Vite on 5173)
Prod mode: build the frontend first; FastAPI then serves frontend/dist too,
so the whole product runs as a single process on one port.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .api import router
from .brain import rules as rules_mod

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Statement Categorizer",
    version=config.APP_VERSION,
    description="Sorts credit-card statements for tax time. "
                "Rule-based brain, no AI model in the decision path.",
)

# Stateless demo tool: permissive CORS keeps local dev (Vite on :5173) simple.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/api/rules-info")
def rules_info() -> dict:
    """Expose the active rule set so the UI/docs can stay in sync."""
    return {"version": rules_mod.rules_version(),
            "categories": rules_mod.all_category_names()}


# Serve the built React app last, so /api routes always win.
if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True),
              name="spa")
