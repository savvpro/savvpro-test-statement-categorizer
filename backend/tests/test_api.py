from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_upload(sample_text):
    store.replace([])
    res = client.post("/upload", files={"file": ("s.csv", sample_text, "text/csv")})
    assert res.status_code == 200
    return res.json()


def test_upload_returns_all_rows(fresh_upload):
    assert len(fresh_upload["transactions"]) == 75
    assert fresh_upload["skipped_rows"] == []
    assert all(t["reason"] and "confidence" in t for t in fresh_upload["transactions"])


def test_upload_replaces_previous_statement(sample_text):
    small = "Date,Description,Debit,Credit,Balance\n01-01-2026,KFC DHA,500,,9500\n"
    res = client.post("/upload", files={"file": ("a.csv", small, "text/csv")})
    assert len(res.json()["transactions"]) == 1
    assert len(client.get("/transactions").json()) == 1


def test_money_is_serialized_as_string():
    assert isinstance(client.get("/transactions").json()[0]["amount"], str)


def test_filters():
    review = client.get("/transactions", params={"needs_review": "true"}).json()
    assert review and all(t["needs_review"] for t in review)
    food = client.get("/transactions", params={"category": "Food"}).json()
    assert food and all(t["category"] == "Food" for t in food)
    assert client.get("/transactions", params={"category": "Nope"}).json() == []


def test_categories_endpoint():
    cats = client.get("/categories").json()
    assert "Entertainment" in cats and "Travel & Transport" in cats
    assert "Needs Review" not in cats


def test_patch_updates_row_and_returns_full_list():
    review = client.get("/transactions", params={"needs_review": "true"}).json()
    target = review[0]
    res = client.patch(f"/transactions/{target['id']}", json={"category": "Shopping"})
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) == 75
    row = next(t for t in rows if t["id"] == target["id"])
    assert row["category"] == "Shopping"
    assert row["user_edited"] and not row["needs_review"]
    assert row["confidence"] == 1.0 and row["reason"] == "Edited by user"


def test_summary_before_and_after_patch():
    before = client.get("/summary").json()
    review = client.get("/transactions", params={"needs_review": "true"}).json()
    target = next(t for t in review if Decimal(t["amount"]) < 0)
    client.patch(f"/transactions/{target['id']}", json={"category": "Shopping"})
    after = client.get("/summary").json()
    assert after["needs_review_count"] == before["needs_review_count"] - 1

    def net(summary, cat):
        return Decimal(next((c["net"] for c in summary["categories"] if c["category"] == cat), 0))

    assert net(after, "Shopping") == net(before, "Shopping") + Decimal(target["amount"])
    assert Decimal(after["total_spending"]) == Decimal(before["total_spending"])


def test_summary_excludes_transfers_and_income_and_nets_refunds(rows):
    summary = client.get("/summary").json()
    debits = sum(-t.amount for t in rows if t.amount < 0 and t.category not in {"Transfer"})
    refunded = sum(t.amount for t in rows if t.category == "Refund" and t.refund_of is not None)
    assert Decimal(summary["total_spending"]) == debits - refunded
    income = sum(t.amount for t in rows if t.category == "Income")
    assert Decimal(summary["total_income"]) == income
    assert refunded > 0


def test_refund_reduces_matching_category(rows):
    refund = next(t for t in rows if t.description == "CAREEM *TRIP REFUND")
    purchase = next(t for t in rows if t.id == refund.refund_of)
    summary = client.get("/summary").json()
    total = next(c for c in summary["categories"] if c["category"] == purchase.category)
    spent = sum(t.amount for t in rows if t.category == purchase.category)
    assert Decimal(total["net"]) == spent + refund.amount


def test_bad_extension():
    res = client.post("/upload", files={"file": ("a.txt", "x", "text/plain")})
    assert res.status_code == 400 and ".csv" in res.json()["detail"]


def test_file_too_large():
    big = "a" * 1_000_001
    res = client.post("/upload", files={"file": ("a.csv", big, "text/csv")})
    assert res.status_code == 400 and "too large" in res.json()["detail"]


def test_missing_columns():
    res = client.post("/upload", files={"file": ("a.csv", "Date,Description\n", "text/csv")})
    assert res.status_code == 400 and "Missing columns" in res.json()["detail"]


def test_no_valid_rows():
    text = "Date,Description,Debit,Credit,Balance\nnot-a-date,X,5,,1\n"
    res = client.post("/upload", files={"file": ("a.csv", text, "text/csv")})
    assert res.status_code == 400 and "No valid rows" in res.json()["detail"]


def test_not_utf8():
    res = client.post("/upload", files={"file": ("a.csv", b"\xff\xfe\x00bad", "text/csv")})
    assert res.status_code == 400


def test_invalid_category():
    res = client.patch("/transactions/1", json={"category": "Pizza"})
    assert res.status_code == 400 and "Invalid category" in res.json()["detail"]


def test_unknown_transaction():
    res = client.patch("/transactions/9999", json={"category": "Food"})
    assert res.status_code == 404
