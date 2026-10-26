from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import statements

app = FastAPI(title="Statement Categorizer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(statements.router)


@app.get("/health")
def health():
    return {"status": "ok"}