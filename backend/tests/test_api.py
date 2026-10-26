from pathlib import Path

import pytest

from app.services.store import get_store

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data" / "fake_statement.csv"
SMALL = b"date,description,amount\n2026-10-04,JOES CAFE 9921,-12.40\n"


@pytest.fixture(autouse=True)
def clean_store():
    get_store().replace([])


def upload(client, content: bytes):
    return client.post("/upload", files={"file": ("test.csv", content, "text/csv")})


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_sample(client):
    r = upload(client, SAMPLE.read_bytes())
    assert r.status_code == 200
    body = r.json()
    assert len(body["transactions"]) == 34
    assert len(body["skipped"]) == 2
    assert body["summary"]["needs_review_count"] > 0


def test_upload_empty_file(client):
    assert upload(client, b"").status_code == 400


def test_upload_missing_columns(client):
    r = upload(client, b"date,description\n2026-10-01,ADOBE\n")
    assert r.status_code == 400
    assert "Missing columns" in r.json()["detail"]


def test_upload_header_only(client):
    assert upload(client, b"date,description,amount\n").status_code == 400


def test_upload_too_large(client, monkeypatch):
    monkeypatch.setattr("app.api.upload.MAX_UPLOAD_BYTES", 10)
    assert upload(client, SMALL).status_code == 413


def test_list_categories(client):
    cats = client.get("/categories").json()
    assert "Needs Review" in cats
    assert "Software" in cats


def test_list_transactions_after_upload(client):
    upload(client, SMALL)
    assert len(client.get("/transactions").json()) == 1


def test_user_fixes_needs_review_row(client):
    upload(client, SMALL)
    r = client.patch("/transactions/row-2", json={"category": "Meals"})
    assert r.status_code == 200
    body = r.json()
    assert body["transaction"]["category"] == "Meals"
    assert body["transaction"]["user_overridden"] is True
    assert body["transaction"]["tax_deductible"] == "partial"
    assert body["summary"]["needs_review_count"] == 0


def test_patch_unknown_category(client):
    upload(client, SMALL)
    r = client.patch("/transactions/row-2", json={"category": "Nonsense"})
    assert r.status_code == 400


def test_patch_unknown_transaction(client):
    r = client.patch("/transactions/row-999", json={"category": "Meals"})
    assert r.status_code == 404