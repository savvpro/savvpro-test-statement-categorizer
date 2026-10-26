"""
Integration tests for FastAPI endpoints.
"""

import io
from decimal import Decimal

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Freelance Ledger" in data["app"]


def test_categories_endpoint():
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert "Software" in data["categories"]
    assert "Needs Review" in data["categories"]
    assert "descriptions" in data


def test_demo_statement_endpoint():
    response = client.post("/api/statements/demo")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "demo_freelancer_statement.csv"
    assert data["total_rows"] > 20
    assert len(data["transactions"]) > 20
    assert "summary" in data
    assert Decimal(str(data["summary"]["total_expenses"])) > 0


def test_preview_statement_upload():
    csv_content = b"""Date,Description,Amount
2026-01-05,ADOBE CREATIVE CLOUD,-59.99
2026-01-06,UBER *TRIP,-24.50
2026-01-07,CLIENT PAYMENT INVOICE #101,1500.00
"""
    files = {"file": ("test_statement.csv", io.BytesIO(csv_content), "text/csv")}
    response = client.post("/api/statements/preview", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["valid_rows"] == 3
    assert len(data["transactions"]) == 3
    assert data["summary"]["total_expenses"] == "84.49"
    assert data["summary"]["total_income"] == "1500.00"


def test_preview_statement_invalid_extension():
    files = {"file": ("test.pdf", io.BytesIO(b"dummy pdf content"), "application/pdf")}
    response = client.post("/api/statements/preview", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_export_endpoint():
    payload = {
        "transactions": [
            {
                "id": "txn_001",
                "date": "2026-01-05",
                "original_date": "2026-01-05",
                "description": "ADOBE CREATIVE CLOUD",
                "normalized_description": "ADOBE CREATIVE CLOUD",
                "amount": "-59.99",
                "direction": "expense",
                "category": "Software",
                "confidence": 0.98,
                "reason": "Matched Adobe",
                "needs_review": False,
                "user_edited": True,
                "notes": "Verified annual software license",
                "is_duplicate": False,
                "duplicate_reason": None,
            }
        ]
    }
    response = client.post("/api/export", json=payload)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers["content-disposition"]
    csv_text = response.text
    assert "ADOBE CREATIVE CLOUD" in csv_text
    assert "Software" in csv_text
    assert "Verified annual software license" in csv_text
