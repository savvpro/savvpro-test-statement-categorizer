from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import transactions, upload
from app.config import CORS_ORIGINS

app = FastAPI(title="Statement Categorizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(transactions.router)


@app.get("/health")
def health():
    return {"status": "ok"}