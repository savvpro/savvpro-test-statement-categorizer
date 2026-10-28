"""End-to-end through the real brain."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import upload
from tests.factories import OFX_V1, OFX_V2, bank_csv


def _items(c: TestClient, sid: str) -> list[dict[str, Any]]:
    return c.get(f"/api/v1/statements/{sid}/transactions").json()["items"]  # type: ignore[no-any-return]


def test_real_brain_csv_pipeline(real_client: TestClient) -> None:
    r = upload(real_client, bank_csv())
    assert r.status_code == 201, r.text
    body = r.json()
    items = _items(real_client, body["id"])
    assert len(items) == 4
    counts = body["counts"]
    assert sum(counts.values()) == 4
    assert counts["duplicate"] == 0
    for i in items:
        if i["status"] == "auto":
            assert i["category"] is not None
            assert i["confidence"] >= 0.85
        elif i["status"] == "needs_review":
            assert i["category"] is None
        assert i["merchant_key"]
    summary = real_client.get(f"/api/v1/statements/{body['id']}/summary").json()
    assert summary["duplicates"]["count"] == 0
    assert summary["unresolved"]["count"] == counts["needs_review"]
    assert summary["total_income_cents"] >= 0 >= summary["total_expense_cents"]


def test_real_brain_ofx_pipelines(real_client: TestClient) -> None:
    a = upload(real_client, OFX_V1, name="a.ofx")
    assert a.status_code == 201, a.text
    assert a.json()["source_format"] == "ofx"
    assert a.json()["row_count"] > 0
    r = upload(real_client, OFX_V2, name="b.ofx", account_type="credit_card")
    assert r.status_code == 201, r.text
    assert r.json()["account_type"] == "credit_card"
    assert r.json()["row_count"] > 0


def test_real_brain_second_upload_flags_overlap(real_client: TestClient) -> None:
    first = upload(real_client, bank_csv()).json()
    r = upload(real_client, bank_csv([("02/10/2026", "SOMETHING NEW", "-9.99")]), name="b.csv")
    assert r.json()["counts"]["duplicate"] == 4
    dups = [i for i in _items(real_client, r.json()["id"]) if i["status"] == "duplicate"]
    first_ids = {i["id"] for i in _items(real_client, first["id"])}
    assert len(dups) == 4
    assert all(d["duplicate_of_id"] in first_ids for d in dups)
