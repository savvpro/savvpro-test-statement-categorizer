import pytest
from fastapi.testclient import TestClient
from app.main import app, SAMPLE_CSV_DATA
from app.models.schemas import CategoryName

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_categories_endpoint():
    res = client.get("/api/categories")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert len(data["categories"]) > 0


def test_load_sample_statement():
    res = client.get("/api/statements/sample")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "transactions" in data
    assert len(data["transactions"]) >= 20
    assert data["summary"]["total_income"] > 0
    assert data["summary"]["total_expenses"] > 0
    assert data["summary"]["needs_review_count"] > 0


def test_upload_statement_csv():
    files = {"file": ("my_statement.csv", SAMPLE_CSV_DATA.encode("utf-8"), "text/csv")}
    res = client.post("/api/statements/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "my_statement.csv"
    assert len(data["transactions"]) > 0


def test_update_category_endpoint():
    # First load sample
    client.get("/api/statements/sample")

    # Update Joe's Cafe to Meals & Entertainment
    payload = {
        "transaction_id": "sample-tx-9",
        "new_category": CategoryName.MEALS_ENTERTAINMENT.value,
        "apply_to_future": True
    }
    res = client.post("/api/transactions/update-category", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Find the updated transaction
    target = next((tx for tx in data["transactions"] if tx["id"] == "sample-tx-9"), None)
    assert target is not None
    assert target["category"] == CategoryName.MEALS_ENTERTAINMENT.value
    assert target["needs_review"] is False
    assert target["user_edited"] is True


def test_export_statement():
    client.get("/api/statements/sample")
    res = client.get("/api/statements/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Date,Original Description" in res.text
