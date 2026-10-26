from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURE = Path(__file__).parents[2] / "fixtures" / "sample_statement.csv"


def upload():
    return client.post("/statements", files={"file": ("s.csv", FIXTURE.read_bytes(), "text/csv")})


def test_upload_and_summary():
    r = upload()
    assert r.status_code == 200
    body = r.json()
    s = body["summary"]
    assert s["category_totals"]["Software"] == 58.99
    assert s["category_totals"]["Office & Equipment"] == 0.0   # purchase fully refunded
    assert s["income_total"] == 3500.0
    assert s["excluded_total"] == 1700.0                       # savings transfer + card payment
    dup = [t for t in body["transactions"] if "duplicate" in t["reason"]]
    assert len(dup) == 1 and dup[0]["needs_review"]


def test_correction_remembers_rule():
    body = upload().json()
    cafe = next(t for t in body["transactions"] if t["description"].startswith("JOES"))
    r = client.patch(f"/statements/{body['id']}/transactions/{cafe['id']}", json={"category": "Meals"})
    assert r.status_code == 200
    again = upload().json()
    assert next(t for t in again["transactions"] if t["description"].startswith("JOES"))["category"] == "Meals"


def test_rejects_bad_input():
    assert client.post("/statements", files={"file": ("a.txt", b"x", "text/plain")}).status_code == 415
    assert client.post("/statements", files={"file": ("a.csv", b"foo,bar\n1,2", "text/csv")}).status_code == 422
    assert client.patch("/statements/nope/transactions/0", json={"category": "Meals"}).status_code == 404
