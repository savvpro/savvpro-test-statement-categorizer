from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.router import api_router
from app.brain.rules import default_rules
from app.core.settings import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    default_rules()  # invalid rules.yaml stops the app at startup, with a clear error
    init_db()
    yield


app = FastAPI(title="Statement Categorizer", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
register_error_handlers(app)
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
