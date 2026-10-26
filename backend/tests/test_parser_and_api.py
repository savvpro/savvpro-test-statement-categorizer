from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.parser import StatementFormatError, parse_amount, parse_csv

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data" / "freelancer_statement.csv"


@pytest.mark.parametrize("raw,expected", [
    ("-54.99", Decimal("-54.99")), ("$1,800.00", Decimal("1800.00")), ("(45.00)", Decimal("-45.00")),
    ("45.00 CR", Decimal("45.00")), ("45.00 DR", Decimal("-45.00")), ("45.00-", Decimal("-45.00")),
])
def test_parse_amount_styles(raw, expected):
    assert parse_amount(raw) == expected


def test_debit_credit_columns_and_preamble():
    csv_text = "My Bank\nDate,Details,Debit,Credit\n2026-09-01,COFFEE,4.50,\n2026-09-02,REFUND,,4.50\nClosing balance,,,\n"
    result = parse_csv(csv_text)
    assert [t.kind.value for t in result.transactions] == ["debit", "credit"]
    assert not result.errors


def test_bad_rows_are_reported_not_dropped():
    result = parse_csv("Date,Description,Amount\n2026-13-45,X,1\n2026-09-01,,2\n")
    assert len(result.errors) == 2 and not result.transactions


def test_not_a_statement():
    with pytest.raises(StatementFormatError):
        parse_csv("foo,bar\n1,2\n")


def test_api_upload_review_and_totals():
    client = TestClient(app)
    r = client.post("/api/statements", files={"file": ("s.csv", SAMPLE.read_bytes(), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["needs_review"] > 0 and len(body["errors"]) == 2
    cafe = next(t for t in body["transactions"] if t["description"].startswith("JOES CAFE"))
    r = client.patch(f"/api/statements/{body['id']}/transactions/{cafe['id']}",
                     json={"category": "Meals (50% deductible)"})
    assert r.status_code == 200
    assert r.json()["summary"]["needs_review"] == body["summary"]["needs_review"] - 1
    assert r.json()["summary"]["by_category"]["Meals (50% deductible)"] == "12.80"


def test_api_rejects_non_csv():
    r = TestClient(app).post("/api/statements", files={"file": ("s.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 415
