from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from categorizer import classify
from main import app, statements


HEADER = "date,description,amount,currency\n"

SAMPLE = HEADER + (
    "2026-10-01,ADOBE CREATIVE CLOUD,-6500,PKR\n"
    "2026-10-02,CLIENT PAYMENT PROJECT ALPHA,50000,PKR\n"
    "2026-10-03,TRANSFER TO SAVINGS,-10000,PKR\n"
    "2026-10-04,UNKNOWN SHOP,-1500,PKR\n"
    "2026-10-05,ADOBE REFUND,2000,PKR\n"
    "2026-10-06,UBER TRIP,-800,PKR\n"
    "2026-10-07,NAYATEL INTERNET,-3500,PKR\n"
)


@pytest.fixture
def client():
    statements.clear()
    with TestClient(app) as test_client:
        yield test_client
    statements.clear()


def upload(client, content=SAMPLE, filename="sample.csv"):
    return client.post(
        "/statements",
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
    )


def test_upload_and_totals(client):
    response = upload(client)

    assert response.status_code == 200
    data = response.json()

    assert data["transaction_count"] == 7
    assert data["needs_review_count"] == 1
    assert data["summary"]["total_income"] == "50000.00"
    assert data["summary"]["net_expenses"] == "8800.00"
    assert data["summary"]["category_net_expenses"]["Software"] == "4500.00"
    assert data["summary"]["transfers_out"] == "10000.00"
    assert data["summary"]["unresolved_outgoing"] == "1500.00"

    # Uploaded statements can be retrieved.
    saved = client.get(f"/statements/{data['statement_id']}")
    assert saved.status_code == 200
    assert saved.json() == data


@pytest.mark.parametrize(
    "description,amount,kind,category,needs_review",
    [
        ("ADOBE", "-100", "expense", "Software", False),
        ("ADOBE REFUND", "100", "refund", "Software", False),
        ("TRANSFER TO SAVINGS", "-100", "transfer", "Transfer", False),
        ("UNKNOWN SHOP", "-100", "unknown", "Needs Review", True),
        ("UNEXPLAINED DEPOSIT", "100", "unknown", "Needs Review", True),
        ("ADOBE REFUND", "-100", "unknown", "Needs Review", True),
        ("ADOBE UBER", "-100", "unknown", "Needs Review", True),
        ("REFUND", "100", "refund", "Needs Review", True),
        ("ADOBE", "0", "unknown", "Needs Review", True),
    ],
)
def test_categorization_rules(
    description, amount, kind, category, needs_review
):
    result = classify(description, Decimal(amount))

    assert result["type"] == kind
    assert result["category"] == category
    assert result["needs_review"] is needs_review


@pytest.mark.parametrize(
    "content",
    [
        "",
        "date,description\n2026-10-01,ADOBE\n",
        HEADER + "2026-02-30,ADOBE,-100,PKR\n",
        HEADER + "2026-10-01,ADOBE,not-money,PKR\n",
        HEADER + "2026-10-01,ADOBE,NaN,PKR\n",
        HEADER + "2026-10-01,ADOBE,-1.234,PKR\n",
        HEADER + "2026-10-01,,-100,PKR\n",
        HEADER + (
            "2026-10-01,ADOBE,-100,PKR\n"
            "2026-10-02,FIGMA,-20,USD\n"
        ),
    ],
)
def test_invalid_csv_is_rejected(client, content):
    response = upload(client, content)

    assert response.status_code == 400
    assert response.json()["detail"]


def test_non_csv_file_is_rejected(client):
    response = upload(client, filename="statement.pdf")
    assert response.status_code == 400


def test_correction_updates_totals(client):
    data = upload(client).json()
    statement_id = data["statement_id"]

    response = client.patch(
        f"/statements/{statement_id}/transactions/4",
        json={"type": "expense", "category": "Office Supplies"},
    )

    assert response.status_code == 200
    updated = response.json()

    assert updated["needs_review_count"] == 0
    assert updated["summary"]["net_expenses"] == "10300.00"
    assert updated["summary"]["unresolved_outgoing"] == "0.00"
    assert updated["transactions"][3]["category"] == "Office Supplies"

    # Confirm the correction is stored, not only returned.
    saved = client.get(f"/statements/{statement_id}").json()
    assert saved == updated


def test_invalid_correction_does_not_change_statement(client):
    data = upload(client).json()
    statement_id = data["statement_id"]

    # An outgoing amount cannot be classified as incoming client income.
    response = client.patch(
        f"/statements/{statement_id}/transactions/4",
        json={"type": "income", "category": "Client Income"},
    )

    assert response.status_code == 400

    saved = client.get(f"/statements/{statement_id}").json()
    assert saved == data


def test_marking_transaction_unknown_removes_it_from_totals(client):
    data = upload(client).json()

    response = client.patch(
        f"/statements/{data['statement_id']}/transactions/6",
        json={"type": "unknown", "category": "Needs Review"},
    )

    assert response.status_code == 200
    updated = response.json()

    assert updated["needs_review_count"] == 2
    assert updated["summary"]["net_expenses"] == "8000.00"
    assert updated["summary"]["unresolved_outgoing"] == "2300.00"


def test_missing_statement_returns_404(client):
    response = client.get("/statements/does-not-exist")
    assert response.status_code == 404


def test_missing_transaction_returns_404(client):
    data = upload(client).json()

    response = client.patch(
        f"/statements/{data['statement_id']}/transactions/999",
        json={"type": "expense", "category": "Software"},
    )

    assert response.status_code == 404