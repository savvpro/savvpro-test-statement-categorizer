import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SAMPLE = Path(__file__).parent.parent / "sample_data" / "freelancer_statement.csv"


def post(content, **data):
    return client.post("/api/categorize", files={"file": ("s.csv", content, "text/csv")}, data=data)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_end_to_end_sample():
    response = post(SAMPLE.read_bytes())
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["needs_review_count"] > 0
    assert body["summary"]["income"] == 2400 + 1850
    assert len(body["issues"]) == 2
    assert isinstance(body["transactions"][0]["amount"], float)


def test_overrides_are_applied():
    response = post(SAMPLE.read_bytes(), overrides=json.dumps({"JOES CAFE": "Meals & Entertainment"}))
    joes = next(t for t in response.json()["transactions"] if "JOES" in t["description"])
    assert joes["category"] == "Meals & Entertainment"


def test_bad_overrides_rejected():
    assert post(SAMPLE.read_bytes(), overrides="[1]").status_code == 422
    assert post(SAMPLE.read_bytes(), overrides="nope").status_code == 422


def test_unusable_file_gives_422_with_message():
    response = post(b"hello world")
    assert response.status_code == 422
    assert "columns" in response.json()["detail"]


def test_oversize_file_rejected():
    assert post(b"a" * (2 * 1024 * 1024 + 10)).status_code == 413
