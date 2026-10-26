import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_categories_endpoint():
    response = client.get("/api/categories")
    assert response.status_code == 200
    categories = response.json()
    assert "Software & Subscriptions" in categories
    assert "Needs Review" in categories


def test_upload_valid_statement():
    csv_content = (
        "Date,Description,Amount\n"
        "2024-03-01,GITHUB INC,-19.00\n"
        "2024-03-05,AMAZON.COM BILL,-45.00\n"
        "2024-03-10,STRIPE PAYOUT,3200.00\n"
    )
    files = {"file": ("statement.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "statement.csv"
    assert len(data["transactions"]) == 3
    assert data["summary"]["total_transactions"] == 3
    assert data["summary"]["total_income"] == 3200.00

    # Amazon should trigger Needs Review
    amazon_tx = next(t for t in data["transactions"] if "AMAZON" in t["raw_description"])
    assert amazon_tx["needs_review"] is True


def test_upload_empty_file_returns_400():
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_invalid_extension_returns_400():
    files = {"file": ("test.exe", io.BytesIO(b"malicious"), "application/octet-stream")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_export_endpoint():
    payload = {
        "filename": "march_statement.csv",
        "transactions": [
            {
                "id": "tx_1",
                "line_number": 1,
                "date": "2024-03-01",
                "raw_description": "GITHUB INC",
                "normalized_description": "GITHUB INC",
                "amount": 19.00,
                "transaction_type": "DEBIT",
                "category": "Software & Subscriptions",
                "confidence": 0.98,
                "reason": "Exact merchant rule",
                "needs_review": False,
                "is_refund": False,
                "is_transfer": False,
                "is_duplicate": False,
                "is_personal_ambiguous": False,
                "user_overridden": False,
                "currency": "USD",
            }
        ],
        "category_totals": [
            {
                "category": "Software & Subscriptions",
                "count": 1,
                "total_amount": 19.00,
                "percentage_of_expenses": 100.0,
            }
        ],
        "summary": {
            "total_transactions": 1,
            "total_income": 0.0,
            "total_expenses": 19.0,
            "total_transfers": 0.0,
            "total_refunds": 0.0,
            "needs_review_count": 0,
            "duplicate_count": 0,
            "review_progress_percent": 100.0,
        },
    }
    response = client.post("/api/export", json=payload)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "GITHUB INC" in response.text
    assert "TAX SUMMARY BREAKDOWN" in response.text
