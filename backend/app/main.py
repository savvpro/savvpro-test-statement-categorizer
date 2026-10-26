
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints.uploads import router as uploads_router
from app.api.endpoints.transactions import router as transactions_router
from app.api.endpoints.reports import router as reports_router
from app.db.database import Base, engine
from app.db import models


app = FastAPI(
    title="Statement Categorizer",
    description="Upload and categorize bank statement transactions.",
    version="0.1.0",
)

# Allow the React/Vite frontend to communicate with FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables.
Base.metadata.create_all(bind=engine)

# Register API routes.
app.include_router(uploads_router)
app.include_router(transactions_router)
app.include_router(reports_router)


@app.get("/")
def root():
    return {
        "message": "Statement Categorizer API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
