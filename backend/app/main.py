"""
TaxSort – Statement Categorizer API

FastAPI application entry point.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, rules, statements, summary, transactions
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TaxSort – Statement Categorizer",
    description=(
        "Categorize bank and credit card statements into IRS Schedule C "
        "expense categories using deterministic rules."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(statements.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(rules.router, prefix="/api/v1")
app.include_router(summary.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
