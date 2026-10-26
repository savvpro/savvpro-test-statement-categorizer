from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.settings import Settings, get_settings
from app.main import app
from app.models import Transaction
from tests.conftest import upload

CARD_HEADER = "Date,Description,Amount,Currency\n"


def card_csv(*lines: str) -> bytes:
    return (CARD_HEADER + "\n".join(lines) + "\n").encode()


@pytest.fixture
def small_limit() -> Iterator[None]:
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, max_upload_mb=1)
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.mark.parametrize(
    ("name", "profile", "account_type", "rows", "errors", "skipped", "review"),
    [
        ("bank_a_card.csv", "bank_a_card", "card", 31, 0, 0, 4),
        ("bank_b_checking.csv", "bank_b_checking", "bank", 25, 0, 0, 5),
        ("messy_statement.csv", "bank_a_card", "card", 10, 4, 1, 2),
    ],
)
def test_upload_sample_files(
    client: TestClient,
    name: str,
    profile: str,
    account_type: str,
    rows: int,
    errors: int,
    skipped: int,
    review: int,
) -> None:
    response = upload(client, name)
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == name
    assert body["profile_name"] == profile and body["account_type"] == account_type
    assert body["row_count"] == rows == len(body["transactions"])
    assert body["parse_error_count"] == errors == len(body["parse_errors"])
    assert body["skipped_count"] == skipped
    assert body["needs_review_count"] == review
    assert sum(t["needs_review"] for t in body["transactions"]) == review
    assert [t["row_number"] for t in body["transactions"]] == sorted(
        t["row_number"] for t in body["transactions"]
    )


def test_upload_returns_decisions_and_string_amounts(client: TestClient) -> None:
    body = upload(client, "bank_a_card.csv").json()
    adobe = body["transactions"][0]
    assert adobe["amount"] == "-59.99" and isinstance(adobe["amount"], str)
    assert adobe["category"] == "Software & Subscriptions"
    assert (adobe["kind"], adobe["rule_id"], adobe["needs_review"]) == ("expense", "adobe", False)
    assert adobe["raw_description"] == "ADOBE CREATIVE CLOUD SAN JOSE CA"
    assert adobe["edited_by_user"] is False
    assert all(isinstance(t["amount"], str) for t in body["transactions"])


def test_messy_file_errors_are_returned_not_dropped(client: TestClient) -> None:
    body = upload(client, "messy_statement.csv").json()
    errors = {e["row_number"]: e for e in body["parse_errors"]}
    assert set(errors) == {4, 5, 12, 15}
    assert "expected 4 columns, got 5" in errors[12]["reason"]
    assert errors[4]["raw_line"] == "2026-09-04,DIGITALOCEAN.COM NEW YORK NY,,USD"
    parsed = {t["row_number"] for t in body["transactions"]}
    assert parsed | set(errors) | {3} == set(range(1, 16))  # every line accounted for


@pytest.mark.parametrize(
    ("amount", "stored"), [("-1850.00", -185000), ("123456789.99", 12345678999), ("-0.01", -1)]
)
def test_money_round_trip(client: TestClient, db: Session, amount: str, stored: int) -> None:
    body = upload(client, "x.csv", card_csv(f"2026-09-01,SOMEWHERE 1,{amount},PKR")).json()
    assert body["transactions"][0]["amount"] == amount
    row = db.get(Transaction, body["transactions"][0]["id"])
    assert row.amount_minor == stored  # an integer in the database, not a float
    assert client.get(f"/api/statements/{body['id']}").json()["transactions"][0]["amount"] == amount


def test_amount_with_too_many_decimals_becomes_a_parse_error(client: TestClient) -> None:
    body = upload(client, "x.csv", card_csv("2026-09-01,SOMEWHERE,-1.005,PKR")).json()
    assert body["transactions"] == []
    assert "decimal places" in body["parse_errors"][0]["reason"]


def test_unknown_format_is_a_400_with_the_supported_formats(client: TestClient) -> None:
    response = upload(client, "other.csv", b"When,What,How much\n2026-09-01,X,-1\n")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "bank_a_card" in detail and "bank_b_checking" in detail
    assert "Date,Description,Amount,Currency" in detail
    assert client.get("/api/statements").json() == []  # nothing was saved


def test_empty_file_is_a_400(client: TestClient) -> None:
    response = upload(client, "empty.csv", b"")
    assert response.status_code == 400 and "empty" in response.json()["detail"].lower()


def test_unreadable_file_is_a_400(client: TestClient) -> None:
    response = upload(client, "bad.csv", b"\xff\xfe\x00bad")
    assert response.status_code == 400 and "UTF-8" in response.json()["detail"]


@pytest.mark.parametrize("name", ["statement.txt", "statement.pdf", "csv", ""])
def test_non_csv_is_a_400(client: TestClient, name: str) -> None:
    response = upload(client, name, card_csv("2026-09-01,X,-1,PKR"))
    assert response.status_code in (400, 422)  # an empty file name is rejected before the route
    if response.status_code == 400:
        assert ".csv" in response.json()["detail"]


def test_uppercase_extension_is_accepted(client: TestClient) -> None:
    assert upload(client, "STATEMENT.CSV", card_csv("2026-09-01,X,-1,PKR")).status_code == 201


def test_missing_file_field_is_a_422(client: TestClient) -> None:
    assert client.post("/api/statements").status_code == 422


@pytest.mark.usefixtures("small_limit")
def test_oversized_upload_is_a_413(client: TestClient) -> None:
    big = CARD_HEADER.encode() + b"2026-09-01,X,-1,PKR\n" * (60_000)  # about 1.2 MB
    response = upload(client, "big.csv", big)
    assert response.status_code == 413
    assert "1 MB" in response.json()["detail"]
    assert client.get("/api/statements").json() == []


@pytest.mark.usefixtures("small_limit")
def test_file_under_the_limit_is_accepted(client: TestClient) -> None:
    assert upload(client, "bank_a_card.csv").status_code == 201


def test_directory_parts_are_removed_from_the_file_name(client: TestClient) -> None:
    body = upload(client, "../../etc/passwd.csv", card_csv("2026-09-01,X,-1,PKR")).json()
    assert body["filename"] == "passwd.csv"


def test_list_and_get(client: TestClient) -> None:
    first = upload(client, "bank_a_card.csv").json()["id"]
    second = upload(client, "messy_statement.csv").json()["id"]
    listing = client.get("/api/statements").json()
    assert [s["id"] for s in listing] == [second, first]  # newest first
    assert listing[0]["row_count"] == 10 and listing[0]["parse_error_count"] == 4
    assert listing[0]["needs_review_count"] == 2 and listing[1]["needs_review_count"] == 4
    assert "transactions" not in listing[0]
    detail = client.get(f"/api/statements/{first}").json()
    assert detail["row_count"] == 31 and len(detail["transactions"]) == 31
    assert detail["uploaded_at"].endswith("Z") or "+" in detail["uploaded_at"]


@pytest.mark.parametrize("path", ["", "/summary", "/export"])
def test_unknown_statement_is_a_404(client: TestClient, path: str) -> None:
    response = client.get(f"/api/statements/999{path}")
    assert response.status_code == 404 and "999" in response.json()["detail"]


def test_categories(client: TestClient) -> None:
    body = client.get("/api/categories").json()
    assert "Needs Review" in body["categories"] and "Tax Withheld" in body["categories"]
    assert body["kinds"] == ["expense", "income", "transfer", "refund", "fee", "tax"]


def test_health_is_kept(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_cors_uses_the_configured_origins(client: TestClient) -> None:
    headers = {"Access-Control-Request-Method": "GET"}
    ok = client.options("/api/categories", headers={**headers, "Origin": "http://localhost:5173"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    bad = client.options("/api/categories", headers={**headers, "Origin": "http://evil.test"})
    assert "access-control-allow-origin" not in bad.headers
