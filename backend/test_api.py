from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "sample_statement.csv"


def upload(content, name="statement.csv"):
    return client.post("/api/categorize", files={"file": (name, content, "text/csv")})


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_sample_statement_end_to_end():
    r = upload(SAMPLE.read_bytes())
    assert r.status_code == 200
    rows = {t["description"]: t for t in r.json()["transactions"]}
    assert rows["ADOBE CREATIVE CLOUD"]["category"] == "Software"
    assert rows["TRANSFER TO SAVINGS"]["kind"] == "transfer"
    assert rows["REFUND ADOBE"]["kind"] == "refund"
    assert rows["CLIENT PAYMENT"]["kind"] == "income"
    assert rows["JOES CAFE 9921"]["category"] == "Needs Review"


def test_rejects_non_csv():
    assert upload(b"x", "notes.txt").status_code == 400


def test_rejects_missing_columns():
    assert upload(b"foo,bar\n1,2\n").status_code == 400


def test_rejects_bad_amount_with_row_number():
    r = upload(b"description,amount\nADOBE,abc\n")
    assert r.status_code == 400
    assert "row 2" in r.json()["detail"]


def test_rejects_empty_statement():
    assert upload(b"description,amount\n").status_code == 400


def test_rejects_non_utf8():
    assert upload(b"description,amount\n\xff\xfe,5\n").status_code == 400


def test_rejects_large_file():
    big = b"description,amount\n" + b"ADOBE,1\n" * (700 * 1024)
    assert upload(big).status_code == 413


def test_debit_credit_columns():
    csv = b"date,description,debit,credit\n2026-10-01,ADOBE,10.00,\n2026-10-02,REFUND ADOBE,,10.00\n"
    r = upload(csv)
    assert r.status_code == 200
    amounts = [t["amount"] for t in r.json()["transactions"]]
    assert amounts == [10.0, -10.0]
    assert r.json()["transactions"][1]["kind"] == "refund"


def test_blank_lines_are_skipped_and_bom_handled():
    r = upload(b"\xef\xbb\xbfDescription,Amount\nADOBE,5\n,\n")
    assert r.status_code == 200 and r.json()["count"] == 1


def test_categories_endpoint_and_patch_validation():
    cats = client.get("/api/categories").json()["categories"]
    assert "Needs Review" in cats
    assert client.patch("/api/transactions/abc", json={"category": "Software"}).status_code == 200
    assert client.patch("/api/transactions/abc", json={"category": "Nope"}).status_code == 400
