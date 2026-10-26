"""API tests using FastAPI TestClient."""


import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import store


@pytest.fixture
def client():
    store.clear()
    return TestClient(app)


def _csv_bytes(lines):
    return "\n".join(lines).encode("utf-8")


class TestUploadAPI:
    def test_upload_amount_column(self, client):
        files = {"file": ("statement.csv", _csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,STARBUCKS,-5.50",
            "2025-01-16,ADOBE CREATIVE CLOUD,-29.99",
            "2025-01-17,NETFLIX,-15.99",
        ]), "text/csv")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["transactions"]) == 3
        assert data["transactions"][0]["category"] == "Meals"
        assert data["transactions"][0]["needs_review"] is False
        assert data["transactions"][1]["category"] == "Software"
        assert data["transactions"][2]["category"] == "Subscriptions"
        assert "summary" in data
        assert "warnings" in data

    def test_upload_debit_credit_column(self, client):
        files = {"file": ("statement.csv", _csv_bytes([
            "Transaction Date,Details,Debit,Credit",
            "01/15/2025,STARBUCKS,$5.50,",
            '01/16/2025,CLIENT PAYMENT,,"$1,000.00"',
        ]), "text/csv")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["transactions"][0]["amount"] == -5.50
        assert data["transactions"][1]["amount"] == 1000.00
        assert data["transactions"][1]["category"] == "Income"

    def test_upload_invalid_file_type(self, client):
        files = {"file": ("statement.txt", b"not a csv", "text/plain")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400

    def test_upload_empty_file(self, client):
        files = {"file": ("empty.csv", b"", "text/csv")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400

    def test_upload_duplicate_rows(self, client):
        files = {"file": ("statement.csv", _csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,ADOBE CREATIVE CLOUD,-29.99",
            "2025-01-15,ADOBE CREATIVE CLOUD,-29.99",
        ]), "text/csv")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["transactions"][0]["is_duplicate"] is False
        assert data["transactions"][1]["is_duplicate"] is True

    def test_upload_tricky_rows(self, client):
        files = {"file": ("statement.csv", _csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,REFUND UBER *TRIP,15.50",
            "2025-01-16,TRANSFER TO SAVINGS 1234,-500.00",
            "2025-01-17,PAYMENT THANK YOU,-1200.00",
            "2025-01-18,INVOICE DEPOSIT CLIENT ACME,2500.00",
            "2025-01-19,,-45.00",
            "2025-01-20,AMZN Mktp US*BOOKS,-22.99",
            "2025-01-21,PAYPAL *EBAY SELLER,-8.75",
        ]), "text/csv")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        tx_map = {t["description"]: t for t in data["transactions"]}
        assert tx_map["REFUND UBER *TRIP"]["category"] == "Refund"
        assert tx_map["TRANSFER TO SAVINGS 1234"]["category"] == "Transfer"
        assert tx_map["PAYMENT THANK YOU"]["category"] == "Transfer"
        assert tx_map["INVOICE DEPOSIT CLIENT ACME"]["category"] == "Income"
        assert tx_map["AMZN Mktp US*BOOKS"]["category"] == "Needs Review"
        assert tx_map["PAYPAL *EBAY SELLER"]["category"] == "Needs Review"
        assert tx_map["AMZN Mktp US*BOOKS"]["needs_review"] is True
        assert tx_map["PAYPAL *EBAY SELLER"]["needs_review"] is True


class TestPatchTransaction:
    def test_update_category(self, client):
        files = {"file": ("statement.csv", _csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,Joes Cafe,-12.00",
        ]), "text/csv")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        tx_id = response.json()["transactions"][0]["id"]

        update = {"category": "Meals"}
        response = client.patch(f"/api/transactions/{tx_id}", json=update)
        assert response.status_code == 200
        data = response.json()
        assert data["transaction"]["category"] == "Meals"
        assert data["transaction"]["reason"] == "user correction"
        assert data["transaction"]["needs_review"] is False

        summary = client.get("/api/summary").json()
        assert summary["totals"]["Meals"] == -12.00

    def test_update_nonexistent(self, client):
        response = client.patch(
            "/api/transactions/00000000-0000-0000-0000-000000000000",
            json={"category": "Meals"},
        )
        assert response.status_code == 404


class TestSummary:
    def test_summary_excludes_transfer(self, client):
        files = {"file": ("statement.csv", _csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,STARBUCKS,-5.50",
            "2025-01-16,TRANSFER TO SAVINGS 1234,-500.00",
        ]), "text/csv")}
        client.post("/api/upload", files=files)
        summary = client.get("/api/summary").json()
        # Transfer is excluded from spending_total
        assert summary["spending_total"] == -5.50
        assert summary["totals"]["Meals"] == -5.50
        assert summary["totals"]["Transfer"] == -500.0

    def test_summary_refund_negative(self, client):
        files = {"file": ("statement.csv", _csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,REFUND UBER *TRIP,15.50",
        ]), "text/csv")}
        client.post("/api/upload", files=files)
        summary = client.get("/api/summary").json()
        assert summary["totals"]["Refund"] == 15.50


class TestExport:
    def test_export_csv(self, client):
        files = {"file": ("statement.csv", _csv_bytes([
            "Date,Description,Amount",
            "2025-01-15,STARBUCKS,-5.50",
        ]), "text/csv")}
        client.post("/api/upload", files=files)
        response = client.get("/api/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        content = response.content.decode("utf-8")
        assert "STARBUCKS" in content
        assert "Meals" in content

