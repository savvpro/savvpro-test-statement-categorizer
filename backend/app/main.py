"""Application entry point: `uvicorn app.main:app`."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="Driver Statement Categorizer",
    version="1.0.0",
    description="Sorts a gig driver's bank and card statements into tax categories with a rule-based brain.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
