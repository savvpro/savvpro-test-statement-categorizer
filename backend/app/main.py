"""HTTP API for Proofsheet."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .categories import public_categories
from .memory import Memory
from .parser import ParseError
from .service import CorrectionError, apply_correction, build_statement, read_upload

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_statements" / "studio_north_january.csv"
DEFAULT_MEMORY = Path(__file__).resolve().parent.parent / "data" / "memory.db"

app = FastAPI(title="Proofsheet", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AppState:
    def __init__(self) -> None:
        self.statements: dict[str, dict] = {}
        self._memory: Memory | None = None
        self.lock = threading.Lock()

    @property
    def memory(self) -> Memory:
        if self._memory is None:
            self._memory = Memory(Path(os.environ.get("PROOFSHEET_MEMORY", DEFAULT_MEMORY)))
        return self._memory

    @memory.setter
    def memory(self, value: Memory) -> None:
        self._memory = value


state = AppState()


class CorrectionIn(BaseModel):
    category: str
    remember: bool = False


class StatementQuery(BaseModel):
    account_type: str = Field(default="credit_card")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/categories")
def categories() -> list[dict[str, str]]:
    return public_categories()


@app.post("/api/statements/sample")
def load_sample(account_type: str = "credit_card") -> dict:
    text = SAMPLE_PATH.read_text(encoding="utf-8")
    return _store("studio_north_january.csv", text, account_type)


@app.post("/api/statements")
async def upload_statement(
    file: UploadFile = File(...),
    account_type: str = Form("credit_card"),
) -> dict:
    payload = await file.read()
    try:
        text = read_upload(file.filename or "", payload)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _store(file.filename or "statement.csv", text, account_type)


@app.get("/api/statements/{statement_id}")
def get_statement(statement_id: str) -> dict:
    statement = state.statements.get(statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found.")
    return statement


@app.patch("/api/statements/{statement_id}/transactions/{transaction_id}")
def correct_transaction(statement_id: str, transaction_id: str, body: CorrectionIn) -> dict:
    with state.lock:
        statement = state.statements.get(statement_id)
        if statement is None:
            raise HTTPException(status_code=404, detail="Statement not found.")
        try:
            updated = apply_correction(statement, transaction_id, body.category, body.remember, state.memory)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Transaction not found.") from exc
        except CorrectionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        state.statements[statement_id] = updated
        return updated


def _store(filename: str, text: str, account_type: str) -> dict:
    try:
        statement = build_statement(filename, text, account_type, state.memory)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    with state.lock:
        state.statements[statement["id"]] = statement
    return statement
