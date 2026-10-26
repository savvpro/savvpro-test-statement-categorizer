import csv
import io
from decimal import Decimal
from pathlib import Path

import pytest
from app import database
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app.state, "db_path", tmp_path / "test.sqlite3")
    with TestClient(app) as client:
        yield client


def upload(client, content, filename="statement.csv"):
    return client.post(
        "/api/statements",
        params={"filename": filename},
        content=content,
        headers={"Content-Type": "text/csv"},
    )


def sample_content():
    return (
        Path(__file__).resolve().parents[2] / "samples" / "developer-signed.csv"
    ).read_bytes()


def test_import_summary_and_reconciliation(client):
    response = upload(client, sample_content())
    assert response.status_code == 201
    detail = response.json()
    assert len(detail["transactions"]) == 18
    assert detail["statement"]["duplicate_count"] == 2
    summary = client.get(f"/api/statements/{detail['statement']['id']}/summary").json()
    assert summary == detail["summary"]
    assert {
        key: summary[key]
        for key in (
            "expenses",
            "income",
            "refunds",
            "transfers",
            "transfers_in",
            "transfers_out",
            "unclassified_in",
            "unclassified_out",
            "net_movement",
            "review_count",
        )
    } == {
        "expenses": "59500.50",
        "income": "250000.00",
        "refunds": "4500.00",
        "transfers": "60000.00",
        "transfers_in": "10000.00",
        "transfers_out": "50000.00",
        "unclassified_in": "12500.00",
        "unclassified_out": "79249.00",
        "net_movement": "88250.50",
        "review_count": 9,
    }
    assert summary["expense_categories"]["Cloud & Hosting"] == "30750.50"
    assert summary["expense_categories"]["Internet & Telecom"] == "6500.00"
    assert summary["currency"] == "PKR"
    assert Decimal(summary["net_movement"]) == (
        Decimal(summary["income"])
        + Decimal(summary["refunds"])
        + Decimal(summary["transfers_in"])
        + Decimal(summary["unclassified_in"])
        - Decimal(summary["expenses"])
        - Decimal(summary["transfers_out"])
        - Decimal(summary["unclassified_out"])
    )


def test_manual_correction_persists_and_retains_original_decision(client):
    detail = upload(client, sample_content()).json()
    statement_id = detail["statement"]["id"]
    cafe = next(
        row
        for row in detail["transactions"]
        if row["description"] == "CAFE CHAI CORNER"
    )
    response = client.patch(
        f"/api/statements/{statement_id}/transactions/{cafe['id']}",
        json={"category": "Meals & Entertainment"},
    )
    assert response.status_code == 200
    assert response.json()["summary"]["expenses"] == "60750.50"
    assert response.json()["summary"]["review_count"] == 8
    with TestClient(app) as reopened:
        saved = reopened.get(f"/api/statements/{statement_id}").json()
        row = next(row for row in saved["transactions"] if row["id"] == cafe["id"])
        assert row["category"] == "Meals & Entertainment"
        assert row["automatic_category"] == "Needs Review"
        assert row["manually_corrected"] is True
        assert row["manual_category"] == "Meals & Entertainment"
        assert row["needs_review"] is False
        assert len(reopened.get("/api/statements").json()) == 1


def test_duplicate_confirmation_does_not_remove_entries(client):
    detail = upload(client, sample_content()).json()
    duplicate = next(row for row in detail["transactions"] if row["possible_duplicate"])
    response = client.post(
        f"/api/statements/1/transactions/{duplicate['id']}/confirm-duplicate",
    )
    rows = response.json()["transactions"]
    confirmed = next(row for row in rows if row["id"] == duplicate["id"])
    assert len(rows) == 18
    assert confirmed["possible_duplicate"] is True
    assert confirmed["needs_review"] is False
    assert confirmed["duplicate_confirmed"] is True
    assert confirmed["manually_corrected"] is False
    assert confirmed["manual_category"] is None
    assert confirmed["category"] == duplicate["category"]
    assert confirmed["automatic_explanation"] == duplicate["automatic_explanation"]
    assert response.json()["summary"]["expenses"] == "59500.50"
    repeated = client.post(
        f"/api/statements/1/transactions/{duplicate['id']}/confirm-duplicate"
    )
    assert repeated.json() == response.json()
    with TestClient(app) as reopened:
        row = next(
            row
            for row in reopened.get("/api/statements/1/transactions").json()
            if row["id"] == duplicate["id"]
        )
        assert row["duplicate_confirmed"] is True
        assert row["manual_category"] is None


def test_manual_choice_overrides_automatic_transfer(client):
    detail = upload(
        client,
        b"Date,Description,Amount\n2026-09-01,TRANSFER TO OWN SAVINGS ACCOUNT,-8000\n",
    ).json()
    row = detail["transactions"][0]
    assert row["category"] == "Transfer"
    updated = client.patch(
        f"/api/statements/1/transactions/{row['id']}",
        json={"category": "Professional Services"},
    ).json()
    assert updated["transactions"][0]["automatic_category"] == "Transfer"
    assert updated["summary"]["transfers"] == "0.00"
    assert updated["summary"]["expenses"] == "8000.00"


@pytest.mark.parametrize(
    "amount,category",
    [
        ("10", "Cloud & Hosting"),
        ("-10", "Client Income"),
        ("-10", "Refund"),
        ("0", "Transfer"),
        ("-10", "Unknown category"),
    ],
)
def test_invalid_corrections_do_not_change_data(client, amount, category):
    detail = upload(
        client, f"Date,Description,Amount\n2026-09-01,UNKNOWN,{amount}\n"
    ).json()
    row = detail["transactions"][0]
    response = client.patch(
        f"/api/statements/1/transactions/{row['id']}", json={"category": category}
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert (
        client.get("/api/statements/1/transactions").json()[0]["manually_corrected"]
        is False
    )


def test_export_preserves_money_and_neutralizes_formulas(client):
    content = 'Date,Description,Amount,Type\n2026-09-01,=HYPERLINK(""bad""),-0.10,@type\n2026-09-02,+SUM(1),-0.20,Card\n2026-09-03,-formula,1,Card\n'
    response = upload(client, content.encode())
    assert response.status_code == 201
    assert response.json()["summary"]["net_movement"] == "0.70"
    response = client.get("/api/statements/1/export")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert [row["Description"][0] for row in rows] == ["'", "'", "'"]
    assert rows[0]["Type"] == "'@type"
    assert rows[0]["Amount"] == "-0.10"
    assert rows[0]["Currency"] == "PKR"
    assert rows[0]["Duplicate confirmed"] == "False"


def test_invalid_import_is_atomic_and_errors_are_consistent(client):
    content = (
        b"Date,Description,Amount\n2026-09-01,VERCEL,-20\n2026-09-02,UNKNOWN,NaN\n"
    )
    response = upload(client, content)
    assert response.status_code == 422
    assert "Row 3" in response.json()["detail"]
    assert client.get("/api/statements").json() == []
    assert upload(client, b"hello", "statement.pdf").status_code == 415
    assert upload(client, b"x" * (1024 * 1024 + 1)).status_code == 413
    assert client.get("/api/statements/999/summary").status_code == 404


def test_transaction_must_belong_to_statement(client):
    upload(client, b"Date,Description,Amount\n2026-09-01,VERCEL,-20\n")
    upload(client, b"Date,Description,Amount\n2026-09-02,GITHUB COPILOT,-19\n")
    assert (
        client.patch(
            "/api/statements/2/transactions/1", json={"category": "Transfer"}
        ).status_code
        == 404
    )


def test_category_changes_and_duplicate_confirmation_are_independent(client):
    detail = upload(
        client,
        b"Date,Description,Amount\n2026-09-01,DARAZ MARKETPLACE,-7999\n2026-09-01,DARAZ MARKETPLACE,-7999\n",
    ).json()
    row = detail["transactions"][0]
    url = f"/api/statements/1/transactions/{row['id']}"
    changed = client.patch(url, json={"category": "Equipment & Supplies"}).json()
    corrected = changed["transactions"][0]
    assert corrected["manually_corrected"] is True
    assert corrected["duplicate_confirmed"] is False
    assert corrected["needs_review"] is True
    assert changed["summary"]["review_count"] == 2
    confirmed = client.post(url + "/confirm-duplicate").json()
    assert confirmed["transactions"][0]["category"] == "Equipment & Supplies"
    assert confirmed["transactions"][0]["needs_review"] is False
    assert confirmed["summary"]["review_count"] == 1
    assert confirmed["summary"]["expenses"] == "7999.00"
    assert confirmed["summary"]["net_movement"] == "-15998.00"
    unknown = detail["transactions"][1]
    confirmed_unknown = client.post(
        f"/api/statements/1/transactions/{unknown['id']}/confirm-duplicate"
    ).json()
    assert confirmed_unknown["transactions"][1]["category"] == "Needs Review"
    assert confirmed_unknown["transactions"][1]["needs_review"] is True
    assert confirmed_unknown["transactions"][1]["manually_corrected"] is False
    assert confirmed_unknown["summary"]["review_count"] == 1
    with TestClient(app) as reopened:
        saved = reopened.get("/api/statements/1").json()
        assert saved["transactions"] == confirmed_unknown["transactions"]


def test_duplicate_confirmation_checks_statement_and_flag(client):
    upload(client, b"Date,Description,Amount\n2026-09-01,VERCEL,-5600\n")
    upload(client, b"Date,Description,Amount\n2026-09-02,GITHUB COPILOT,-5600\n")
    assert (
        client.post("/api/statements/1/transactions/1/confirm-duplicate").status_code
        == 422
    )
    assert (
        client.post("/api/statements/2/transactions/1/confirm-duplicate").status_code
        == 404
    )
    assert (
        client.post("/api/statements/999/transactions/1/confirm-duplicate").status_code
        == 404
    )


def test_schema_adjustment_is_idempotent_and_preserves_records(client):
    upload(client, b"Date,Description,Amount\n2026-09-01,VERCEL,-5600\n")
    client.patch(
        "/api/statements/1/transactions/1",
        json={"category": "Software & Subscriptions"},
    )
    with database.connect(app.state.db_path) as connection:
        connection.execute("ALTER TABLE transactions DROP COLUMN duplicate_confirmed")
    database.initialize_database(app.state.db_path)
    database.initialize_database(app.state.db_path)
    saved = client.get("/api/statements/1/transactions").json()[0]
    assert saved["amount"] == "-5600.00"
    assert saved["category"] == "Software & Subscriptions"
    assert saved["manual_category"] == "Software & Subscriptions"
    assert saved["duplicate_confirmed"] is False


def test_explicit_eur_is_rejected_without_partial_import(client):
    response = upload(
        client,
        b"Date,Description,Amount,Currency\n2026-09-01,VERCEL,-5600,PKR\n2026-09-02,GITHUB COPILOT,-19,EUR\n",
    )
    assert response.status_code == 422
    assert "Row 3" in response.json()["detail"]
    assert client.get("/api/statements").json() == []


def test_debit_credit_sample_has_reconciled_pkr_totals(client):
    content = (
        Path(__file__).resolve().parents[2] / "samples/developer-debit-credit.csv"
    ).read_bytes()
    detail = upload(client, content).json()
    summary = detail["summary"]
    assert summary["expenses"] == "18400.00"
    assert summary["income"] == "175000.00"
    assert summary["refunds"] == "1400.00"
    assert summary["transfers"] == "33000.00"
    assert summary["unclassified_in"] == "6000.00"
    assert summary["unclassified_out"] == "26500.00"
    assert summary["net_movement"] == "120500.00"
    assert summary["review_count"] == 4
