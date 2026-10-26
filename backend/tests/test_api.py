import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CSV = """Transaction Date,Description,Amount
01/15/2025,ADOBE CREATIVE CLOUD,-52.99
01/16/2025,JOES CAFE 9921,-8.00
"""


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_categorize_upload():
    files = {"file": ("statement.csv", io.BytesIO(CSV.encode()), "text/csv")}
    resp = client.post("/api/categorize", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["transactions"]) == 2
    assert data["needs_review_count"] >= 1


def test_update_category():
    files = {"file": ("statement.csv", io.BytesIO(CSV.encode()), "text/csv")}
    upload = client.post("/api/categorize", files=files).json()
    tx_id = upload["transactions"][1]["id"]
    patch = client.patch(
        "/api/transactions",
        json={"transaction_id": tx_id, "category": "Meals & Entertainment"},
    )
    assert patch.status_code == 200
    updated = next(t for t in patch.json()["transactions"] if t["id"] == tx_id)
    assert updated["user_category"] == "Meals & Entertainment"
