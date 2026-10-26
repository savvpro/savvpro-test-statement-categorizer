"""HTTP API (FastAPI)."""
from __future__ import annotations

import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import Category
from .parser import StatementFormatError
from .service import NotFound, StatementService

MAX_UPLOAD_BYTES = 2 * 1024 * 1024

app = FastAPI(title="Statement Categorizer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
service = StatementService()


class ReviewIn(BaseModel):
    category: Category
    apply_to_same_merchant: bool = True


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/categories")
def categories() -> list[str]:
    return [c.value for c in Category]


@app.post("/api/statements")
async def upload(file: UploadFile = File(...)) -> dict:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(415, "Please upload a .csv statement export.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 2 MB.")
    try:
        return service.upload(file.filename, content)
    except StatementFormatError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/statements/{sid}")
def get_statement(sid: str) -> dict:
    try:
        return service.view(sid)
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc


@app.patch("/api/statements/{sid}/transactions/{tx_id}")
def review(sid: str, tx_id: str, body: ReviewIn) -> dict:
    try:
        return service.review(sid, tx_id, body.category, body.apply_to_same_merchant)
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc
