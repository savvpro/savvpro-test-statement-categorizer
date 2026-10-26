"""API integration tests using FastAPI TestClient."""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app

# ── In-memory SQLite for tests ──────────────────────────────────────────────

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def _override_session():
    with Session(_engine) as session:
        yield session


app.dependency_overrides[get_session] = _override_session


@pytest.fixture(autouse=True)
def setup_db():
    """Create fresh tables before each test."""
    SQLModel.metadata.create_all(_engine)
    yield
    SQLModel.metadata.drop_all(_engine)


client = TestClient(app)

# ── Sample CSV ──────────────────────────────────────────────────────────────

SAMPLE_CSV = (
    "Date,Description,Amount\n"
    "01/04/2026,ADOBE CREATIVE CLOUD,-59.99\n"
    "01/05/2026,PAYMENT THANK YOU,1500.00\n"
    "01/07/2026,SQ *JOES CAFE 9921,-14.20\n"
    "01/09/2026,GOOGLE ADS 4829102,-250.00\n"
    "01/14/2026,STRIPE PAYOUT,3200.00\n"
    "01/15/2026,TRANSFER TO CHECKING,-500.00\n"
)


def _upload(csv_content: str = SAMPLE_CSV, filename: str = "test.csv"):
    """Helper to upload a CSV."""
    return client.post(
        "/api/v1/statements",
        files={"file": (filename, io.BytesIO(csv_content.encode()), "text/csv")},
        data={"account_type": "credit_card"},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Upload
# ═══════════════════════════════════════════════════════════════════════════

class TestUpload:
    def test_upload_success(self):
        resp = _upload()
        assert resp.status_code == 200
        data = resp.json()
        assert data["statement"]["row_count"] == 6
        assert data["counts"]["total"] == 6

    def test_upload_duplicate_rejected(self):
        _upload()
        resp = _upload()
        assert resp.status_code == 409

    def test_upload_bad_file_type(self):
        resp = client.post(
            "/api/v1/statements",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
            data={"account_type": "credit_card"},
        )
        assert resp.status_code == 400

    def test_upload_unrecognized_headers(self):
        bad_csv = "Col1,Col2,Col3\na,b,c\n"
        resp = _upload(bad_csv, "bad.csv")
        assert resp.status_code == 422
        body = resp.json()
        assert "available_columns" in body["detail"]


# ═══════════════════════════════════════════════════════════════════════════
# Statements list
# ═══════════════════════════════════════════════════════════════════════════

class TestStatements:
    def test_list_empty(self):
        resp = client.get("/api/v1/statements")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_upload(self):
        _upload()
        resp = client.get("/api/v1/statements")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_by_id(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        resp = client.get(f"/api/v1/statements/{sid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sid

    def test_get_not_found(self):
        resp = client.get("/api/v1/statements/999")
        assert resp.status_code == 404

    def test_delete(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        resp = client.delete(f"/api/v1/statements/{sid}")
        assert resp.status_code == 200
        # Verify gone
        resp2 = client.get(f"/api/v1/statements/{sid}")
        assert resp2.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Transactions
# ═══════════════════════════════════════════════════════════════════════════

class TestTransactions:
    def test_list_transactions(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        resp = client.get(f"/api/v1/transactions?statement_id={sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6
        assert len(data["items"]) == 6

    def test_filter_by_status(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        resp = client.get(f"/api/v1/transactions?statement_id={sid}&status=auto")
        assert resp.status_code == 200
        # All auto items should have auto status
        for item in resp.json()["items"]:
            assert item["status"] == "auto"

    def test_search(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        resp = client.get(f"/api/v1/transactions?statement_id={sid}&q=ADOBE")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_patch_transaction(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        # Get first transaction
        txns = client.get(f"/api/v1/transactions?statement_id={sid}").json()
        txn_id = txns["items"][0]["id"]
        # Patch it
        resp = client.patch(
            f"/api/v1/transactions/{txn_id}",
            json={"category": "meals", "save_rule": False},
        )
        assert resp.status_code == 200
        assert resp.json()["category"] == "meals"
        assert resp.json()["status"] == "user_confirmed"
        assert resp.json()["confidence"] == 1.0

    def test_patch_with_save_rule(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        txns = client.get(f"/api/v1/transactions?statement_id={sid}").json()
        txn_id = txns["items"][0]["id"]
        # Patch with save_rule
        resp = client.patch(
            f"/api/v1/transactions/{txn_id}",
            json={"category": "meals", "save_rule": True},
        )
        assert resp.status_code == 200
        assert resp.json()["rule_id"] is not None
        # Verify rule was created
        rules = client.get("/api/v1/rules").json()
        assert len(rules) >= 1

    def test_patch_invalid_category(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        txns = client.get(f"/api/v1/transactions?statement_id={sid}").json()
        txn_id = txns["items"][0]["id"]
        resp = client.patch(
            f"/api/v1/transactions/{txn_id}",
            json={"category": "nonexistent"},
        )
        assert resp.status_code == 400

    def test_bulk_update(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        txns = client.get(f"/api/v1/transactions?statement_id={sid}").json()
        ids = [t["id"] for t in txns["items"][:2]]
        resp = client.post(
            "/api/v1/transactions/bulk",
            json={"ids": ids, "category": "office_supplies", "save_rule": False},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        for item in resp.json():
            assert item["category"] == "office_supplies"


# ═══════════════════════════════════════════════════════════════════════════
# Rules
# ═══════════════════════════════════════════════════════════════════════════

class TestRules:
    def test_create_and_list(self):
        resp = client.post(
            "/api/v1/rules",
            json={"pattern": "JOES CAFE", "category": "meals", "match_type": "exact"},
        )
        assert resp.status_code == 200
        rule = resp.json()
        assert rule["pattern"] == "JOES CAFE"

        rules = client.get("/api/v1/rules").json()
        assert len(rules) == 1

    def test_delete_rule(self):
        resp = client.post(
            "/api/v1/rules",
            json={"pattern": "TEST", "category": "meals"},
        )
        rid = resp.json()["id"]
        del_resp = client.delete(f"/api/v1/rules/{rid}")
        assert del_resp.status_code == 200
        assert len(client.get("/api/v1/rules").json()) == 0

    def test_invalid_category(self):
        resp = client.post(
            "/api/v1/rules",
            json={"pattern": "X", "category": "fake_category"},
        )
        assert resp.status_code == 400

    def test_test_rule(self):
        # Upload some data first
        _upload()
        resp = client.post(
            "/api/v1/rules/test",
            json={"pattern": "ADOBE", "category": "software_subscriptions", "match_type": "contains"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["would_match"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Summary and Export
# ═══════════════════════════════════════════════════════════════════════════

class TestSummary:
    def test_summary(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        resp = client.get(f"/api/v1/statements/{sid}/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["statement_id"] == sid
        assert len(data["totals"]) > 0
        assert "status_counts" in data

    def test_export_csv(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        resp = client.get(f"/api/v1/statements/{sid}/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        # Verify content has rows
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 2  # header + at least 1 row

    def test_export_xlsx(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        resp = client.get(f"/api/v1/statements/{sid}/export?format=xlsx")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]

    def test_recategorize(self):
        up = _upload()
        sid = up.json()["statement"]["id"]
        # Add a rule
        client.post(
            "/api/v1/rules",
            json={"pattern": "JOES CAFE", "category": "meals", "match_type": "contains"},
        )
        # Re-run
        resp = client.post(f"/api/v1/statements/{sid}/recategorize")
        assert resp.status_code == 200
        assert resp.json()["total"] == 6


class TestHealth:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
