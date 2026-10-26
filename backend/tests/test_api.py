import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Category
from app.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    store.clear()
    yield
    store.clear()


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_sample_csv_download():
    res = client.get("/api/statements/sample")
    assert res.status_code == 200
    assert "Date,Description,Amount" in res.text


def test_upload_valid_csv():
    csv_content = """Date,Description,Amount
2026-03-01,STRIPE PAYOUT CLIENT INVOICE 1042,3200.00
2026-03-02,ADOBE CREATIVE CLOUD,-54.99
2026-03-03,TRANSFER TO SAVINGS,-1000.00
"""
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/statements/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test.csv"
    assert len(data["transactions"]) == 3
    assert data["summary"]["total_income"] == 3200.00
    assert data["summary"]["total_expenses"] == 54.99
    assert data["summary"]["transfers_total"] == 1000.00


def test_upload_invalid_file_extension():
    files = {"file": ("test.txt", io.BytesIO(b"dummy text"), "text/plain")}
    res = client.post("/api/statements/upload", files=files)
    assert res.status_code == 400
    assert "Invalid file format" in res.json()["detail"]


def test_upload_malformed_csv():
    bad_csv = "Broken,Header\n123"
    files = {"file": ("bad.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")}
    res = client.post("/api/statements/upload", files=files)
    assert res.status_code == 400
    assert "Missing required Date column" in res.json()["detail"]


def test_patch_transaction_correction_and_summary_recalculation():
    csv_content = """Date,Description,Amount
2026-03-01,UNKNOWN VENDOR 992,-150.00
"""
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/statements/upload", files=files)
    tx_id = upload_res.json()["transactions"][0]["id"]
    assert upload_res.json()["transactions"][0]["category"] == "Needs Review"
    assert upload_res.json()["summary"]["needs_review_count"] == 1

    # Now correct it to Office Supplies
    patch_res = client.patch(
        f"/api/transactions/{tx_id}",
        json={"category": "Office Supplies"}
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert patch_data["transaction"]["category"] == "Office Supplies"
    assert patch_data["transaction"]["status"] == "manual"
    assert patch_data["transaction"]["is_reviewed"] is True
    assert patch_data["summary"]["needs_review_count"] == 0


def test_patch_transaction_invalid_category():
    # Attempt to patch with a non-existent category
    patch_res = client.patch(
        "/api/transactions/tx_fake",
        json={"category": "NonExistentCategory"}
    )
    assert patch_res.status_code == 422  # Unprocessable Entity (Pydantic validation failure)


def test_patch_transaction_not_found():
    patch_res = client.patch(
        "/api/transactions/tx_nonexistent",
        json={"category": "Software"}
    )
    assert patch_res.status_code == 404
