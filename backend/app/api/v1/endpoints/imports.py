from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import ConflictError
from app.services.import_service import commit_draft, create_draft

router = APIRouter(prefix="/imports", tags=["imports"])
Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("", status_code=201)
async def upload_file(
    file: UploadFile,
    db: Db,
) -> dict[str, Any]:
    """Step 1: upload file, get draft id + preview."""
    data = await file.read()
    filename = file.filename or "upload.csv"
    try:
        return await create_draft(db, data, filename)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("DUPLICATE_FILE:"):
            stmt_id = msg.split(":", 1)[1]
            raise ConflictError(
                "This file has already been imported",
                details={"statement_id": stmt_id},
            ) from e
        raise HTTPException(status_code=422, detail=msg) from e


@router.post("/{draft_id}/commit", status_code=201)
async def commit_import(
    draft_id: str,
    db: Db,
    account_id: str = Form(...),
    invert_sign: bool | None = Form(None),
    prefer_mdy: bool = Form(True),
) -> dict[str, Any]:
    """Step 2: finalize import with account + toggle overrides."""
    try:
        return await commit_draft(
            db, draft_id, account_id,
            invert_sign=invert_sign,
            prefer_mdy=prefer_mdy,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
