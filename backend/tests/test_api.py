from fastapi.testclient import TestClient

from app import rules
from app.main import app

client = TestClient(app)

CSV = (b"Date,Description,Amount\n"
       b"2026-09-01,ADOBE CREATIVE CLOUD,-20.00\n"
       b"2026-09-02,JOES CAFE 9921,-8.50\n")


def _upload(content=CSV, name="s.csv", **form):
    return client.post("/api/categorize",
                       files={"file": (name, content, "text/csv")}, data=form)


def test_categories_endpoint():
    r = client.get("/api/categories")
    assert r.status_code == 200
    assert "Income" in r.json()["categories"]


def test_upload_returns_rows_and_summary():
    r = _upload()
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) == 2
    assert "needs_review_count" in body["summary"]
    assert body["skipped"] == []


def test_user_rule_is_applied():
    category = next(iter(rules.CATEGORIES))
    r = _upload(user_rules='{"JOES CAFE": "%s"}' % category)
    row = r.json()["rows"][1]
    assert row["category"] == category
    assert row["needs_review"] is False


def test_rejects_non_csv():
    assert _upload(name="s.pdf").status_code == 400


def test_rejects_missing_columns():
    assert _upload(content=b"foo,bar\n1,2\n").status_code == 400


def test_rejects_unknown_user_category():
    assert _upload(user_rules='{"X": "Not A Category"}').status_code == 400


def test_rejects_bad_json():
    assert _upload(user_rules="{oops").status_code == 400