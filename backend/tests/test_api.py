from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app, state
from app.memory import Memory

SAMPLE = (Path(__file__).resolve().parents[1] / "sample_statements" / "studio_north_january.csv").read_text(
    encoding="utf-8"
)


@pytest.fixture
def client(tmp_path):
    state.memory = Memory(tmp_path / "memory.db")
    state.statements.clear()
    return TestClient(app)


def test_sample_statement_totals(client):
    response = client.post("/api/statements/sample")
    assert response.status_code == 200
    body = response.json()
    by_description = {item["description"]: item for item in body["transactions"]}

    assert by_description["JOES CAFE 9921 BROOKLYN NY"]["needs_review"] is True
    assert by_description["PAYMENT THANK YOU"]["category"] == "card_payment"
    assert by_description["TRANSFER TO SAVINGS"]["category"] == "transfer"
    assert by_description["ADOBE *CREATIVE CLOUD REFUND"]["category"] == "refund"
    assert by_description["ADOBE *CREATIVE CLOUD REFUND"]["offsets_category"] == "software"
    assert by_description["STRIPE PAYOUT"]["category"] == "income"
    assert by_description["T-MOBILE*AUTO PAY"]["needs_review"] is True
    assert by_description["LEGALZOOM.COM"]["needs_review"] is True
    assert by_description["SEPHORA TIMES SQUARE"]["category"] == "personal"
    assert by_description["PENDING UBER *TRIP"]["pending"] is True
    assert by_description["PENDING UBER *TRIP"]["category"] == "travel"

    duplicates = [item for item in body["transactions"] if item["duplicate"]]
    assert len(duplicates) == 1
    assert duplicates[0]["description"].startswith("STAPLES")

    summary = body["summary"]
    assert summary["deductible_total"] == pytest.approx(2150.25)
    assert summary["income_total"] == pytest.approx(1340)
    assert summary["excluded_total"] == pytest.approx(1500)
    assert summary["personal_total"] == pytest.approx(42)
    assert summary["needs_review_count"] == 13
    software = next(item for item in summary["categories"] if item["id"] == "software")
    equipment = next(item for item in summary["categories"] if item["id"] == "equipment")
    assert software["total"] == pytest.approx(119.97)
    assert equipment["total"] == pytest.approx(369)


def test_upload_and_correction_updates_similar_rows(client):
    response = client.post(
        "/api/statements",
        files={"file": ("studio.csv", SAMPLE.encode("utf-8"), "text/csv")},
        data={"account_type": "credit_card"},
    )
    assert response.status_code == 200
    body = response.json()
    cafe = next(item for item in body["transactions"] if item["description"].startswith("JOES CAFE"))
    updated = client.patch(
        f"/api/statements/{body['id']}/transactions/{cafe['id']}",
        json={"category": "meals", "remember": True},
    )
    assert updated.status_code == 200
    rows = updated.json()["transactions"]
    confirmed = [item for item in rows if item["fingerprint"] == "JOES CAFE"]
    assert len(confirmed) == 2
    assert all(item["category"] == "meals" and item["needs_review"] is False for item in confirmed)

    again = client.post("/api/statements/sample")
    learned = [
        item
        for item in again.json()["transactions"]
        if item["fingerprint"] == "JOES CAFE" and "TST" not in item["description"] and "JOES CAFE" in item["description"]
    ]
    # Both the plain cafe and the Toast line share the saved merchant.
    saved_rows = [item for item in again.json()["transactions"] if item["fingerprint"] == "JOES CAFE"]
    assert learned
    assert all(item["category"] == "meals" and item["source"] == "memory" for item in saved_rows)


def test_confirming_a_duplicate_lets_it_count(client):
    body = client.post("/api/statements/sample").json()
    duplicate = next(item for item in body["transactions"] if item["duplicate"])
    updated = client.patch(
        f"/api/statements/{body['id']}/transactions/{duplicate['id']}",
        json={"category": "supplies", "remember": False},
    )
    summary = updated.json()["summary"]
    supplies = next(item for item in summary["categories"] if item["id"] == "supplies")
    assert supplies["total"] == pytest.approx(84.34)
    assert summary["needs_review_count"] == 12


def test_positive_refund_in_a_file_becomes_money_back(client):
    csv_text = "Date,Description,Amount\n01/02/2026,ADOBE REFUND,54.99\n"
    response = client.post(
        "/api/statements",
        files={"file": ("refund.csv", csv_text, "text/csv")},
        data={"account_type": "credit_card"},
    )
    row = response.json()["transactions"][0]
    assert row["category"] == "refund"
    assert row["offsets_category"] == "software"
    assert row["amount"] == pytest.approx(-54.99)
    assert response.json()["summary"]["deductible_total"] == pytest.approx(-54.99)


def test_rejects_non_csv_and_unknown_category(client):
    rejected = client.post(
        "/api/statements",
        files={"file": ("notes.pdf", b"%PDF", "application/pdf")},
        data={"account_type": "credit_card"},
    )
    assert rejected.status_code == 400
    body = client.post("/api/statements/sample").json()
    bad = client.patch(
        f"/api/statements/{body['id']}/transactions/{body['transactions'][0]['id']}",
        json={"category": "yacht"},
    )
    assert bad.status_code == 400


def test_health_and_categories(client):
    assert client.get("/api/health").json()["status"] == "ok"
    labels = {item["id"] for item in client.get("/api/categories").json()}
    assert "software" in labels
    assert "needs_review" not in labels
