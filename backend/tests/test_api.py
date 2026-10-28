from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def upload(content: bytes, name: str = "statement.csv"):
    return client.post("/api/statements", files={"file": (name, content, "text/csv")})


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_upload_returns_rows_and_summary(sample):
    res = upload(sample("checking_bank_style.csv"))
    assert res.status_code == 201
    body = res.json()
    assert body["summary"]["transactions"] == len(body["transactions"]) == 22
    assert len(body["statement"]["skipped"]) == 2


def test_rejects_non_csv_and_bad_files():
    assert upload(b"hello", "statement.pdf").status_code == 415
    assert upload(b"Foo,Bar\n1,2\n").status_code == 422


def test_fix_applies_to_similar_rows_and_is_remembered():
    csv = b"Date,Description,Amount\n09/01/2026,ACME WIDGETS 001,-10\n09/02/2026,ACME WIDGETS 002,-12\n"
    body = upload(csv).json()
    first = body["transactions"][0]
    assert first["category"] == "Needs Review"

    fixed = client.patch(f"/api/transactions/{first['id']}", json={"category": "Driver Supplies"}).json()
    assert {t["category"] for t in fixed["transactions"]} == {"Driver Supplies"}
    assert fixed["summary"]["needs_review"] == 0

    # The next statement already knows this merchant.
    again = upload(csv).json()
    assert again["transactions"][0]["category"] == "Driver Supplies"
    assert again["transactions"][0]["rule"] == "learned"


def test_fix_rejects_unknown_category(sample):
    tid = upload(sample("checking_bank_style.csv")).json()["transactions"][0]["id"]
    assert client.patch(f"/api/transactions/{tid}", json={"category": "Snacks"}).status_code == 422
    assert client.patch("/api/transactions/99999", json={"category": "Fuel"}).status_code == 404


def test_export_csv(sample):
    sid = upload(sample("credit_card_style.csv")).json()["statement"]["id"]
    res = client.get(f"/api/statements/{sid}/export.csv")
    assert res.status_code == 200
    assert res.text.splitlines()[0].startswith("Date,Description,Amount,Category")


def test_list_and_delete(sample):
    sid = upload(sample("debit_credit_columns.csv")).json()["statement"]["id"]
    assert any(s["id"] == sid for s in client.get("/api/statements").json())
    assert client.delete(f"/api/statements/{sid}").status_code == 204
    assert client.get(f"/api/statements/{sid}").status_code == 404
