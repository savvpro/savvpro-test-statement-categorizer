from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CSV = (b"date,description,amount\n"
       b"2026-10-01,ADOBE CREATIVE CLOUD,-54.99\n"
       b"2026-10-06,AMAZON REFUND,29.99\n"
       b"2026-10-07,AMAZON MARKETPLACE,-45.00\n"
       b"2026-10-07,AMAZON MARKETPLACE,-45.00\n")


def upload(name, content):
    return client.post("/api/upload", files={"file": (name, content, "text/csv")})


def test_upload_ok():
    body = upload("s.csv", CSV).json()
    assert [r["category"] for r in body["rows"]] == [
        "Software", "Refund", "Needs Review", "Needs Review"]
    assert body["rows"][3]["possible_duplicate"] is True
    assert body["totals"]["Software"] == "-54.99"
    assert body["totals"]["Needs Review"] == "-90.00"


def test_wrong_extension():
    assert upload("s.txt", CSV).status_code == 400


def test_empty_csv():
    assert upload("s.csv", b"").status_code == 422


def test_missing_columns():
    assert upload("s.csv", b"a,b\n1,2\n").status_code == 422


def test_too_large():
    assert upload("s.csv", b"x" * (2 * 1024 * 1024 + 1)).status_code == 413


def test_totals_after_user_fix():
    rows = [{"amount": "-10.00", "category": "Meals"},
            {"amount": "-5.50", "category": "Meals"}]
    res = client.post("/api/totals", json={"rows": rows})
    assert res.json()["totals"] == {"Meals": "-15.50"}


def test_totals_rejects_unknown_category():
    res = client.post("/api/totals", json={"rows": [{"amount": "-1", "category": "Hacking"}]})
    assert res.status_code == 422
