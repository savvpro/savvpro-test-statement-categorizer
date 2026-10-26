from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import uploads, transactions, rules

app = FastAPI(title="Statement Categorizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploads.router)
app.include_router(transactions.router)
app.include_router(rules.router)

@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}