from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routes import _csv_safe
from app.main import app
from app.services.store import store

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample_statement.csv"
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_store():
    store.clear()
    yield
    store.clear()


def upload_sample():
    with open(SAMPLE, "rb") as f:
        return client.post("/api/uploads", files={"file": ("sample_statement.csv", f, "text/csv")})


def find(txns, text):
    return [t for t in txns if text in t["description"]]


def usd(summary):
    return next(c for c in summary["currencies"] if c["currency"] == "USD")


def test_upload_sample_returns_rows_and_summary():
    r = upload_sample()
    assert r.status_code == 201
    body = r.json()
    assert len(body["transactions"]) > 30
    assert body["summary"]["invalid_count"] >= 2
    assert body["summary"]["needs_review_count"] > 0


def test_currencies_are_never_mixed():
    currencies = {c["currency"] for c in upload_sample().json()["summary"]["currencies"]}
    assert {"USD", "EUR", "GBP"} <= currencies


def test_exact_duplicate_is_flagged_not_deleted():
    slack = find(upload_sample().json()["transactions"], "SLACK")
    assert len(slack) == 2
    assert [t["is_duplicate"] for t in slack] == [False, True]
    assert slack[1]["duplicate_of"] == slack[0]["id"]


def test_refund_is_not_income():
    refund = find(upload_sample().json()["transactions"], "AMZN Mktp US REFUND")[0]
    assert refund["category"] == "Refund"
    assert Decimal(refund["amount"]) < 0


def test_unknown_merchant_needs_review():
    mystery = find(upload_sample().json()["transactions"], "MYSTERY")[0]
    assert mystery["needs_review"] and mystery["category"] == "Needs Review"


def test_keep_duplicate_adds_it_back_to_totals():
    body = upload_sample().json()
    before = Decimal(usd(body["summary"])["spend_by_category"]["Software"])
    dup = find(body["transactions"], "SLACK")[1]
    r = client.patch(
        f"/api/uploads/{body['upload_id']}/transactions/{dup['id']}",
        json={"keep_duplicate": True},
    )
    assert r.status_code == 200
    after = Decimal(usd(r.json()["summary"])["spend_by_category"]["Software"])
    assert after - before == Decimal("8.75")


def test_correction_updates_row_and_summary():
    body = upload_sample().json()
    mystery = find(body["transactions"], "MYSTERY")[0]
    r = client.patch(
        f"/api/uploads/{body['upload_id']}/transactions/{mystery['id']}",
        json={"category": "Software"},
    )
    assert r.status_code == 200
    out = r.json()["transaction"]
    assert out["category"] == "Software" and not out["needs_review"] and out["user_corrected"]
    assert r.json()["summary"]["needs_review_count"] == body["summary"]["needs_review_count"] - 1


def test_correction_applies_to_same_merchant_rows():
    body = upload_sample().json()
    joes = find(body["transactions"], "JOES CAFE")
    assert len(joes) == 2
    r = client.patch(
        f"/api/uploads/{body['upload_id']}/transactions/{joes[0]['id']}",
        json={"category": "Meals"},
    )
    assert r.json()["also_updated"] == 1
    again = client.get(f"/api/uploads/{body['upload_id']}").json()["transactions"]
    assert all(t["category"] == "Meals" for t in find(again, "JOES CAFE"))


def test_learned_correction_carries_to_next_upload():
    body = upload_sample().json()
    joes = find(body["transactions"], "JOES CAFE")[0]
    client.patch(
        f"/api/uploads/{body['upload_id']}/transactions/{joes['id']}",
        json={"category": "Meals"},
    )
    second = upload_sample().json()["transactions"]
    rows = find(second, "JOES CAFE")
    assert all(t["category"] == "Meals" and t["confidence"] == 1.0 for t in rows)


def test_unknown_category_rejected():
    body = upload_sample().json()
    r = client.patch(
        f"/api/uploads/{body['upload_id']}/transactions/1",
        json={"category": "Nonsense"},
    )
    assert r.status_code == 422


def test_empty_patch_body_rejected():
    body = upload_sample().json()
    r = client.patch(f"/api/uploads/{body['upload_id']}/transactions/1", json={})
    assert r.status_code == 422


def test_unreadable_row_cannot_be_categorized():
    body = upload_sample().json()
    bad = next(t for t in body["transactions"] if t["errors"])
    r = client.patch(
        f"/api/uploads/{body['upload_id']}/transactions/{bad['id']}",
        json={"category": "Software"},
    )
    assert r.status_code == 409


def test_unknown_upload_is_404():
    assert client.get("/api/uploads/doesnotexist").status_code == 404


def test_rejects_non_csv_file():
    r = client.post("/api/uploads", files={"file": ("notes.pdf", b"x", "application/pdf")})
    assert r.status_code == 415


def test_rejects_empty_file():
    r = client.post("/api/uploads", files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400


def test_export_csv():
    body = upload_sample().json()
    r = client.get(f"/api/uploads/{body['upload_id']}/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0].startswith("date,description,amount")


def test_csv_formula_injection_guard():
    assert _csv_safe("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert _csv_safe("ADOBE") == "ADOBE"


def test_categories_endpoint():
    cats = client.get("/api/categories").json()
    assert "Software" in cats and "Needs Review" not in cats


def test_correction_does_not_propagate_to_incoming_transaction():
    csv_data = (
        "date,description,amount,currency\n"
        "2026-01-01,JOES CAFE 1001,12.50,USD\n"
        "2026-01-02,JOES CAFE 1002,-12.50,USD\n"
    )
    r = client.post(
        "/api/uploads",
        files={"file": ("test.csv", csv_data.encode(), "text/csv")},
    )
    assert r.status_code == 201
    body = r.json()
    outgoing = next(t for t in body["transactions"] if Decimal(t["amount"]) > 0)
    incoming = next(t for t in body["transactions"] if Decimal(t["amount"]) < 0)

    corrected = client.patch(
        f"/api/uploads/{body['upload_id']}/transactions/{outgoing['id']}",
        json={"category": "Meals"},
    )
    assert corrected.status_code == 200

    rows = client.get(f"/api/uploads/{body['upload_id']}").json()["transactions"]
    credit = next(t for t in rows if t["id"] == incoming["id"])
    assert credit["category"] == "Needs Review"


def test_incoming_correction_does_not_train_outgoing_merchant_memory():
    csv_data = (
        "date,description,amount,currency\n"
        "2026-01-01,JOES CAFE 1001,-12.50,USD\n"
    )
    first = client.post(
        "/api/uploads",
        files={"file": ("credit.csv", csv_data.encode(), "text/csv")},
    ).json()
    row = first["transactions"][0]

    corrected = client.patch(
        f"/api/uploads/{first['upload_id']}/transactions/{row['id']}",
        json={"category": "Refund"},
    )
    assert corrected.status_code == 200

    second_csv = (
        "date,description,amount,currency\n"
        "2026-01-02,JOES CAFE 1002,12.50,USD\n"
    )
    second = client.post(
        "/api/uploads",
        files={"file": ("debit.csv", second_csv.encode(), "text/csv")},
    ).json()
    assert second["transactions"][0]["category"] == "Needs Review"
