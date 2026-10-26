import pytest
from fastapi.testclient import TestClient

from app.main import app, classify, parse_statement


client = TestClient(app)


def test_known_merchant_is_categorized_with_high_confidence():
    assert classify("ADOBE CREATIVE CLOUD", -59.99) == (
        "Software",
        "high",
        "Matched the 'adobe' merchant rule.",
    )


def test_unknown_merchant_goes_to_review():
    category, confidence, reason = classify("JOES CAFE 9921", -18.25)
    assert category == "Needs review"
    assert confidence == "low"
    assert "No trusted" in reason


def test_refund_is_not_income():
    category, _, _ = classify("ADOBE REFUND", 59.99)
    assert category == "Refund"


def test_statement_requires_expected_headers():
    with pytest.raises(Exception):
        parse_statement(b"when,what\n2026-01-01,coffee")


def test_upload_returns_transactions_and_summary():
    csv = b"Date,Description,Amount\n2026-01-02,FIGMA,-15\n2026-01-03,JOES CAFE 9921,-12.50\n"
    response = client.post(
        "/api/statements",
        files={"file": ("statement.csv", csv, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transactions"][0]["category"] == "Software"
    assert body["transactions"][1]["category"] == "Needs review"
    assert body["summary"]["Software"] == -15


def test_demo_login_and_protected_dashboard():
    login = client.post(
        "/api/auth/login",
        json={"email": "demo@studioledger.com", "password": "demo123"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    dashboard = client.get(f"/api/dashboard?token={token}")
    assert dashboard.status_code == 200
    assert len(dashboard.json()["transactions"]) == 5


def test_dashboard_requires_login():
    assert client.get("/api/dashboard").status_code == 401
