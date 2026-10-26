from fastapi import APIRouter

from app.api import meta, statements, transactions

api_router = APIRouter(prefix="/api")
api_router.include_router(statements.router)
api_router.include_router(transactions.router)
api_router.include_router(meta.router)
