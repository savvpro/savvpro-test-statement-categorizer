from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SAMPLE = Path(__file__).parent.parent / "sample_data" / "statement.csv"


def upload(content: bytes, name="s.csv", **data):
    return client.post("/api/statements", files={"file": (name, content)}, data=data)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_upload_sample_statement():
    response = upload(SAMPLE.read_bytes())
    assert response.status_code == 200
    body = response.json()
    by_desc = {r["description"]: r for r in body["rows"]}
    assert by_desc["ADOBE CREATIVE CLOUD"]["category"] == "Software"
    assert by_desc["TRANSFER TO SAVINGS"]["category"] == "Not Spending"
    assert by_desc["XYZ CONSULTING LTD"]["status"] == "needs_review"
    assert by_desc["REFUND ADOBE CREATIVE CLOUD"]["category"] == "Refund"
    assert len(body["errors"]) == 1  # the 'not-a-date' row
    assert body["summary"]["needs_review_count"] >= 2


def test_duplicates_flagged():
    body = upload(SAMPLE.read_bytes()).json()
    dupes = [r for r in body["rows"] if r["possible_duplicate"]]
    assert len(dupes) == 2 and all("STARBUCKS" in r["description"] for r in dupes)


def test_refund_reduces_category_total():
    body = upload(b"Date,Description,Amount\n2026-09-01,ADOBE,50\n2026-09-02,REFUND ADOBE,-20").json()
    assert body["summary"]["by_category"]["Software"] == 30.0
    assert body["summary"]["refunds"] == 20.0


def test_rejects_non_csv():
    assert upload(b"x", name="s.pdf").status_code == 400


def test_rejects_bad_columns():
    response = upload(b"Foo,Bar\n1,2")
    assert response.status_code == 400 and "Missing column" in response.json()["detail"]


def test_rejects_big_file():
    assert upload(b"a" * (2 * 1024 * 1024 + 10)).status_code == 413


def test_summary_endpoint_after_user_fix():
    rows = [{"id": 1, "amount": -10.0, "category": "Travel"},
            {"id": 2, "amount": -5.0, "category": "Needs Review"}]
    body = client.post("/api/summary", json={"rows": rows}).json()
    assert body["by_category"]["Travel"] == 10.0
    assert body["needs_review_count"] == 1
