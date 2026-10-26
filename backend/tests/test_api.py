import csv
import io

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app

CSV = b"""transaction_id,date,description,amount,currency
one,2026-10-01,ADOBE,-59.99,USD
two,2026-10-02,ADOBE REFUND,10,USD
three,2026-10-03,TRANSFER TO SAVINGS,-500,USD
four,2026-10-04,CLIENT PAYMENT FICTIONAL STUDIO,1000,USD
five,2026-10-05,JOES CAFE,-12.75,USD
"""


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as client:
        yield client


def upload(client, data=CSV, name="sample.csv", **options):
    return client.post("/api/statements", files={"file": (name, data, "text/csv")}, data=options)


def test_import_summaries_exclude_transfers_and_pending_rows(client):
    response = upload(client)
    assert response.status_code == 201
    statement = response.json()
    assert statement["summary"]["net_expenses_cents"] == 4999
    assert statement["summary"]["income_cents"] == 100000
    assert statement["summary"]["needs_review"] == 1
    assert statement["summary"]["pending_outflow_cents"] == 1275
    assert statement["summary"]["categories"] == {"Software": 4999}


def test_import_is_idempotent_and_does_not_reset_edits(client):
    first = upload(client).json()
    row = first["transactions"][-1]
    client.patch(
        f"/api/statements/{first['id']}/transactions/{row['id']}",
        json={
            "category": "Personal",
            "kind": "personal",
            "note": "Personal lunch",
            "revision": 0,
        },
    )
    second = upload(client)
    assert second.status_code == 200
    assert second.json()["id"] == first["id"]
    assert second.json()["transactions"][-1]["category"] == "Personal"
    assert len(client.get("/api/statements").json()) == 1


def test_review_persists_with_history_and_updates_totals(client):
    statement = upload(client).json()
    row = statement["transactions"][-1]
    url = f"/api/statements/{statement['id']}/transactions/{row['id']}"
    response = client.patch(
        url,
        json={
            "category": "Meals",
            "kind": "expense",
            "note": "Client meeting",
            "revision": 0,
        },
    )
    assert response.status_code == 200
    updated = client.get(f"/api/statements/{statement['id']}").json()
    assert updated["summary"]["net_expenses_cents"] == 6274
    assert updated["summary"]["needs_review"] == 0
    row = updated["transactions"][-1]
    assert row["status"] == "reviewed"
    assert row["revision"] == 1
    assert row["original_category"] is None
    assert row["history"][0]["note"] == "Client meeting"
    assert (
        client.patch(
            url,
            json={
                "category": "Other",
                "kind": "expense",
                "revision": 0,
            },
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "category,kind",
    [("Software", "income"), ("Travel", "refund"), ("Made up", "expense"), ("Transfer", "expense")],
)
def test_inconsistent_manual_decisions_rejected(client, category, kind):
    statement = upload(client).json()
    row = statement["transactions"][0]
    response = client.patch(
        f"/api/statements/{statement['id']}/transactions/{row['id']}",
        json={"category": category, "kind": kind, "revision": 0},
    )
    assert response.status_code == 422


def test_invalid_file_leaves_no_partial_statement(client):
    response = upload(client, CSV + b"bad,not-a-date,ADOBE,-4,USD\n")
    assert response.status_code == 422
    assert "Row 7" in response.json()["detail"]
    assert client.get("/api/statements").json() == []


def test_duplicate_rows_held_for_review_until_resolved(client):
    data = b"date,description,amount\n2026-10-01,ADOBE,-10\n2026-10-01,ADOBE,-10"
    statement = upload(client, data).json()
    assert statement["summary"]["net_expenses_cents"] == 1000
    assert statement["summary"]["needs_review"] == 1
    row = statement["transactions"][1]
    response = client.patch(
        f"/api/statements/{statement['id']}/transactions/{row['id']}",
        json={"category": "Excluded", "kind": "excluded", "revision": 0},
    )
    assert response.status_code == 200
    assert response.json()["summary"]["net_expenses_cents"] == 1000
    assert response.json()["summary"]["needs_review"] == 0


def test_csv_export_escapes_formula_text_and_includes_pending_status(client):
    statement = upload(client, b"date,description,amount\n2026-10-01,=SUM(A1:A2),-10").json()
    response = client.get(f"/api/statements/{statement['id']}/export")
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert rows[0]["description"] == "'=SUM(A1:A2)"
    assert rows[0]["status"] == "needs_review"
    assert rows[0]["amount"] == "-10.00"


def test_wrong_extension_unknown_id_and_cross_origin_write(client):
    assert upload(client, name="file.pdf").status_code == 422
    assert client.get("/api/statements/missing").status_code == 404
    assert (
        client.post(
            "/api/statements",
            headers={"Origin": "https://other.example"},
            files={"file": ("x.csv", CSV)},
        ).status_code
        == 403
    )


def test_saved_data_survives_new_app_instance(tmp_path):
    path = tmp_path / "persistent.db"
    with TestClient(create_app(path)) as first:
        statement = upload(first).json()
    with TestClient(create_app(path)) as second:
        assert second.get(f"/api/statements/{statement['id']}").status_code == 200


def test_request_size_limit_and_malformed_headers(client):
    assert (
        client.post(
            "/api/statements",
            headers={
                "Content-Length": str(6 * 1024 * 1024),
            },
            content=b"",
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/api/statements",
            headers={
                "Content-Length": "invalid",
            },
            content=b"",
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/statements",
            headers={
                "Origin": "http://[",
            },
            content=b"",
        ).status_code
        == 403
    )


def test_sample_downloads_and_safe_lookup(client):
    response = client.get("/api/samples/freelancer_statement.csv")
    assert response.status_code == 200
    assert len(list(csv.DictReader(io.StringIO(response.text)))) == 28
    assert client.get("/api/samples/unknown.csv").status_code == 404


def test_health_accepts_render_host(client):
    response = client.get(
        "/api/health",
        headers={"host": "ledgerly-statement-categorizer.onrender.com"},
    )
    assert response.status_code == 200


def test_health_rejects_unknown_host(client):
    response = client.get("/api/health", headers={"host": "untrusted.example"})
    assert response.status_code == 400
