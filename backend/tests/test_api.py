"""
API Integration tests for FastAPI endpoints using TestClient.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_categories():
    res = client.get("/api/categories")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert len(data["categories"]) > 0


def test_list_sample_statements():
    res = client.get("/api/sample-statements")
    assert res.status_code == 200
    samples = res.json()
    assert len(samples) == 3
    ids = [s["id"] for s in samples]
    assert "freelance-cc" in ids


def test_load_sample_freelance_cc():
    res = client.get("/api/sample-statements/freelance-cc")
    assert res.status_code == 200
    data = res.json()
    assert "transactions" in data
    assert "tax_summary" in data
    assert len(data["transactions"]) > 0
    # Check that Joe's Cafe is present and needs review
    joes = [tx for tx in data["transactions"] if "JOES CAFE" in tx["raw_description"]]
    assert len(joes) == 1
    assert joes[0]["needs_review"] is True


def test_upload_statement_csv():
    csv_data = "Date,Description,Amount\n2024-10-01,ADOBE CREATIVE CLOUD,-54.99\n2024-10-02,UBER TRIP,-25.00\n"
    files = {"file": ("test.csv", csv_data, "text/csv")}
    res = client.post("/api/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert len(data["transactions"]) == 2
    assert data["transactions"][0]["category"] == "Software & SaaS Subscriptions"
    assert data["transactions"][1]["category"] == "Travel & Transit"
