"""
Integration tests for FastAPI endpoints using TestClient.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


def test_api_categories():
    res = client.get("/api/categories")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 13
    assert "Software & Subscriptions" in data
    assert "Meals & Client Entertainment" in data
    assert data["Meals & Client Entertainment"]["deductible_percentage"] == 0.5


def test_api_sample_endpoint():
    res = client.get("/api/sample")
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "sample_statement.csv"
    assert data["parsed_count"] == 33
    assert len(data["transactions"]) == 33
    assert "summary" in data
    assert data["summary"]["gross_income"] == 11700.0


def test_api_upload_valid_csv():
    sample_path = SAMPLE_DIR / "sample_statement.csv"
    with open(sample_path, "rb") as f:
        res = client.post(
            "/api/upload",
            files={"file": ("my_statement.csv", f, "text/csv")},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "my_statement.csv"
    assert data["parsed_count"] == 33
    assert len(data["transactions"]) == 33


def test_api_upload_invalid_extension():
    res = client.post(
        "/api/upload",
        files={"file": ("statement.txt", b"some text", "text/plain")},
    )
    assert res.status_code == 400
    assert "Only .csv files are supported" in res.json()["detail"]


def test_api_upload_malformed_csv():
    res = client.post(
        "/api/upload",
        files={"file": ("bad.csv", b"colA,colB\n1,2", "text/csv")},
    )
    assert res.status_code == 400
    assert "CSV format error" in res.json()["detail"]


def test_api_recalculate():
    # First get a categorized sample
    sample_res = client.get("/api/sample")
    sample_data = sample_res.json()
    txs = sample_data["transactions"]

    # Change first transaction to Meals & Client Entertainment and approve
    txs[0]["category"] = "Meals & Client Entertainment"
    txs[0]["deductible_percentage"] = 0.5
    txs[0]["deductible_amount"] = 12.50
    txs[0]["status"] = "MANUALLY_APPROVED"
    txs[0]["needs_review"] = False

    recalc_res = client.post("/api/recalculate", json={"transactions": txs})
    assert recalc_res.status_code == 200
    summary = recalc_res.json()
    assert summary["total_transactions"] == 33
    assert "gross_income" in summary
    assert "total_deductible_expenses" in summary
