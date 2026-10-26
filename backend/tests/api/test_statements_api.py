import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Transaction
from tests.api.helpers import ACCOUNTS, SAMPLES, upload_bytes, upload_sample


@pytest.mark.parametrize("name", sorted(ACCOUNTS))
def test_upload_each_sample(client: TestClient, name: str) -> None:
    body = upload_sample(client, name)
    assert body["filename"] == name
    assert body["row_count"] == len(body["transactions"]) > 0
    assert body["detected_format"]["file_type"] == name.rsplit(".", 1)[1]
    assert body["review_count"] == sum(t["status"] == "needs_review" for t in body["transactions"])
    assert all(isinstance(t["amount"], str) for t in body["transactions"])


def test_messy_upload_keeps_parse_errors_and_warnings(client: TestClient) -> None:
    created = upload_sample(client, "bank_messy.csv")
    detail = client.get(f"/api/statements/{created['id']}").json()
    assert len(detail["parse_errors"]) == 1
    assert {"line_no", "reason", "raw"} <= set(detail["parse_errors"][0])
    assert detail["warnings"]
    assert detail["detected_format"]["delimiter"] is not None


def test_duplicate_upload_returns_409_with_existing_id(client: TestClient) -> None:
    first = upload_sample(client, "credit_card.csv")
    content = (SAMPLES / "credit_card.csv").read_bytes()
    response = upload_bytes(client, "renamed.csv", content, "credit_card")
    assert response.status_code == 409
    assert response.json()["statement_id"] == first["id"]
    assert response.json()["code"] == "duplicate_statement"


def test_oversize_upload_is_413(client: TestClient) -> None:
    content = b"Date,Description,Amount\n" + b"x" * (5 * 1024 * 1024)
    response = upload_bytes(client, "big.csv", content)
    assert response.status_code == 413
    assert "5 MB" in response.json()["detail"]


@pytest.mark.parametrize("name", ["statement.pdf", "statement.xls", "noext"])
def test_wrong_file_type_is_400(client: TestClient, name: str) -> None:
    response = upload_bytes(client, name, b"Date,Description,Amount\n01/02/2026,X,1.00\n")
    assert response.status_code == 400
    assert ".csv and .xlsx" in response.json()["detail"]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"hello there\nthis is not a statement\n", "no header row"),
        (b"", "empty"),
        (b"PK\x03\x04garbage", "could not read"),
    ],
)
def test_junk_file_is_400_with_clear_message(
    client: TestClient, content: bytes, message: str
) -> None:
    response = upload_bytes(
        client, "junk.csv" if not content.startswith(b"PK") else "junk.xlsx", content
    )
    assert response.status_code == 400
    assert message in response.json()["detail"]
    assert client.get("/api/statements").json() == []


def test_missing_account_type_is_422(client: TestClient) -> None:
    content = (SAMPLES / "checking_simple.csv").read_bytes()
    response = client.post("/api/statements", files={"file": ("a.csv", content)})
    assert response.status_code == 422
    assert "account_type" in response.json()["detail"]


def test_list_and_get_statements(client: TestClient) -> None:
    a = upload_sample(client, "checking_simple.csv")
    b = upload_sample(client, "credit_card.csv")
    listed = client.get("/api/statements").json()
    assert {s["id"] for s in listed} == {a["id"], b["id"]}
    assert client.get(f"/api/statements/{a['id']}").json()["filename"] == "checking_simple.csv"
    missing = client.get("/api/statements/999")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "statement 999 not found", "code": "not_found"}


def test_filter_transactions_by_status(client: TestClient) -> None:
    body = upload_sample(client, "credit_card.csv")
    url = f"/api/statements/{body['id']}/transactions"
    everything = client.get(url).json()
    review = client.get(url, params={"status": "needs_review"}).json()
    auto = client.get(url, params={"status": "auto"}).json()
    assert len(everything) == 50
    assert len(review) == body["review_count"] == 14
    assert len(review) + len(auto) == 50
    assert {t["status"] for t in review} == {"needs_review"}
    assert client.get(url, params={"status": "bogus"}).status_code == 422


def test_delete_cascades_to_transactions(client: TestClient, db: Session) -> None:
    body = upload_sample(client, "checking_simple.csv")
    txn_id = body["transactions"][0]["id"]
    assert client.delete(f"/api/statements/{body['id']}").status_code == 204
    assert client.get(f"/api/statements/{body['id']}").status_code == 404
    assert (
        client.patch(f"/api/transactions/{txn_id}", json={"category_id": "meals"}).status_code
        == 404
    )
    assert client.delete(f"/api/statements/{body['id']}").status_code == 404
    assert db.scalar(select(func.count()).select_from(Transaction)) == 0
    # The same file can be uploaded again once its statement is gone.
    assert upload_sample(client, "checking_simple.csv")["row_count"] == 45


def test_export_csv(client: TestClient) -> None:
    body = upload_sample(client, "credit_card.csv")
    response = client.get(f"/api/statements/{body['id']}/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "credit_card-categorized.csv" in response.headers["content-disposition"]
    lines = response.text.splitlines()
    assert lines[0] == "date,description,amount,category,schedule_c_line,status,confidence,reasons"
    assert len(lines) == 1 + 50
    assert lines[1].startswith("2026-01-03,ADOBE CREATIVE CLOUD,-59.99,Software & Subscriptions,")


def test_export_neutralises_formula_descriptions(client: TestClient) -> None:
    content = b'Date,Description,Amount\n01/02/2026,"=HYPERLINK(""x"")",-5.00\n'
    body = upload_bytes(client, "evil.csv", content).json()
    text = client.get(f"/api/statements/{body['id']}/export.csv").text
    assert "'=HYPERLINK" in text


@pytest.mark.parametrize("name", sorted(ACCOUNTS))
def test_samples_are_served(client: TestClient, name: str) -> None:
    response = client.get(f"/api/samples/{name}")
    assert response.status_code == 200
    assert response.content == (SAMPLES / name).read_bytes()


@pytest.mark.parametrize("name", ["README.md", "..%2FTASK.md", "labels", "nope.csv"])
def test_samples_allowlist(client: TestClient, name: str) -> None:
    assert client.get(f"/api/samples/{name}").status_code == 404
