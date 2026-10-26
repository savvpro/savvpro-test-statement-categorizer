from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    return {"status": "ok", "service": "ledgerline-api"}
