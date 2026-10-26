import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import StatementStore, get_store

DATA = Path(__file__).parent.parent / "data"
LOAN = {
    "original_principal": "200000",
    "annual_rate_percent": "6",
    "term_months": 360,
    "first_payment_date": "2025-01-01",
}


@pytest.fixture
def client():
    store = StatementStore()  # a fresh, empty store for every test
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def upload(client, content: bytes, name="statement.csv", loan=None):
    data = {"loan": json.dumps(loan)} if loan else {}
    return client.post("/api/statements", files={"file": (name, content, "text/csv")}, data=data)


def sample(name="bank_a.csv") -> bytes:
    return (DATA / name).read_bytes()


def totals(body):
    return {t["category"]: Decimal(t["total"]) for t in body["summary"]["totals"]}


# ----------------------------------------------------------------- upload
def test_upload_sample_statement(client):
    response = upload(client, sample())
    assert response.status_code == 201
    body = response.json()
    assert len(body["transactions"]) == 87
    assert body["parse_errors"] == []
    assert body["summary"]["duplicate_count"] == 1
    assert body["summary"]["needs_review_count"] == 15  # 12 mortgage + 3 unknown/ambiguous
    assert "Mortgage Interest" not in totals(body)  # no loan details yet


def test_both_bank_formats_give_identical_totals(client):
    a = upload(client, sample("bank_a.csv")).json()
    b = upload(client, sample("bank_b.csv")).json()
    assert totals(a) == totals(b)


def test_upload_with_loan_splits_mortgage_into_totals(client):
    body = upload(client, sample(), loan=LOAN).json()
    found = totals(body)
    assert body["summary"]["needs_review_count"] == 3
    assert "Mortgage Payment" not in found
    assert found["Mortgage Interest"] + found["Mortgage Principal"] == Decimal("-14389.20")
    assert found["Mortgage Interest"] < Decimal("-11000")  # roughly 12 x ~$990


def test_upload_can_be_fetched_again(client):
    created = upload(client, sample()).json()
    fetched = client.get(f"/api/statements/{created['id']}")
    assert fetched.status_code == 200 and fetched.json() == created


# ------------------------------------------------------------- bad input
def test_rejects_non_csv_file(client):
    assert upload(client, b"hello", name="notes.txt").status_code == 400


def test_rejects_empty_file(client):
    assert upload(client, b"").status_code == 422


def test_rejects_file_with_unknown_columns(client):
    assert upload(client, b"Foo,Bar\n1,2\n").status_code == 422


def test_rejects_file_with_only_bad_rows(client):
    response = upload(client, b"Date,Description,Amount\nnope,X,abc\n")
    assert response.status_code == 422


def test_rejects_oversized_file(client):
    big = b"Date,Description,Amount\n" + b"01/01/2025,X,1.00\n" * 200_000
    assert upload(client, big).status_code == 413


def test_bad_rows_are_reported_but_rest_still_loads(client):
    csv_bytes = b"Date,Description,Amount\n01/05/2025,RENT FROM TENANT,1500\nnope,X,abc\n"
    body = upload(client, csv_bytes).json()
    assert len(body["transactions"]) == 1 and len(body["parse_errors"]) == 1


def test_rejects_invalid_loan_details(client):
    bad = dict(LOAN, term_months=0)
    response = upload(client, sample(), loan=bad)
    assert response.status_code == 422 and "term_months" in response.json()["detail"]


def test_unknown_statement_returns_404(client):
    assert client.get("/api/statements/nope").status_code == 404


# ------------------------------------------------------------ corrections
SIMILAR = (
    b"Date,Description,Amount\n"
    b"01/05/2025,JOES CAFE 9921,-18.50\n"
    b"01/09/2025,JOES CAFE 1234,-9.00\n"
    b"01/10/2025,ZELLE FROM JOHN TENANT,1500.00\n"
)


def test_correction_is_applied_to_all_similar_rows(client):
    created = upload(client, SIMILAR).json()
    assert created["summary"]["needs_review_count"] == 2

    response = client.patch(
        f"/api/statements/{created['id']}/transactions/1", json={"category": "Utilities"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["needs_review_count"] == 0
    assert [t["category"] for t in body["transactions"]][:2] == ["Utilities", "Utilities"]
    assert body["transactions"][2]["category"] == "Rental Income"  # untouched


def test_cannot_pick_needs_review_or_mortgage_categories_by_hand(client):
    created = upload(client, SIMILAR).json()
    url = f"/api/statements/{created['id']}/transactions/1"
    for category in ("Needs Review", "Mortgage Payment", "Mortgage Interest"):
        assert client.patch(url, json={"category": category}).status_code == 422


def test_correction_with_unknown_category_or_row(client):
    created = upload(client, SIMILAR).json()
    base = f"/api/statements/{created['id']}/transactions"
    assert client.patch(f"{base}/1", json={"category": "Bogus"}).status_code == 422
    assert client.patch(f"{base}/999", json={"category": "Utilities"}).status_code == 404
    assert client.patch("/api/statements/nope/transactions/1",
                        json={"category": "Utilities"}).status_code == 404


# -------------------------------------------------------- loan afterwards
def test_adding_loan_details_later_resolves_mortgage_rows(client):
    created = upload(client, sample()).json()
    assert created["summary"]["needs_review_count"] == 15

    response = client.put(f"/api/statements/{created['id']}/loan", json=LOAN)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["needs_review_count"] == 3
    assert body["loan"]["term_months"] == 360


def test_wrong_loan_details_leave_mortgage_rows_in_review(client):
    created = upload(client, sample()).json()
    wrong = dict(LOAN, annual_rate_percent="4.5")  # payment would not match
    body = client.put(f"/api/statements/{created['id']}/loan", json=wrong).json()
    assert body["summary"]["needs_review_count"] == 15
    assert any("could not be split" in t["explanation"] for t in body["transactions"])


def test_manual_choice_beats_mortgage_split(client):
    created = upload(client, sample(), loan=LOAN).json()
    mortgage_row = next(t for t in created["transactions"] if "MTG" in t["normalized"])
    # A hand-picked category is remembered and wins over the automatic split.
    response = client.patch(
        f"/api/statements/{created['id']}/transactions/{mortgage_row['id']}",
        json={"category": "Repairs & Maintenance"},
    )
    assert response.status_code == 200
    body = response.json()
    assert all(t["splits"] == [] for t in body["transactions"] if "MTG" in t["normalized"])