"""Integration tests for the FastAPI endpoints."""
from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import create_tables
from app.main import app


@pytest.fixture(scope="module")
async def client():
    # ASGITransport does not trigger lifespan – create tables manually
    await create_tables()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_seed_and_dashboard(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/demo/seed")
    assert resp.status_code in (200, 201)

    resp = await client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "income_cents" in data
    assert "needs_review_count" in data


@pytest.mark.asyncio
async def test_list_accounts(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/accounts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_account(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/accounts", json={
        "name": "Test Checking", "type": "checking", "institution": "Test Bank", "mask": "0000"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Checking"
    return data["id"]


@pytest.mark.asyncio
async def test_upload_csv(client: AsyncClient) -> None:
    csv_data = (
        "Date,Description,Amount\n"
        "01/15/2026,ADOBE CREATIVE CLOUD,-54.99\n"
        "01/16/2026,STARBUCKS,-8.50\n"
        "01/17/2026,STRIPE TRANSFER,150.00\n"
    )
    # First create an account
    acc_resp = await client.post("/api/v1/accounts", json={
        "name": "CSV Test Account", "type": "checking", "institution": "Test Bank", "mask": "9999"
    })
    account_id = acc_resp.json()["id"]

    # Upload
    resp = await client.post(
        "/api/v1/imports",
        files={"file": ("test.csv", io.BytesIO(csv_data.encode()), "text/csv")},
    )
    assert resp.status_code == 201
    draft_id = resp.json()["draft_id"]

    # Commit
    resp = await client.post(
        f"/api/v1/imports/{draft_id}/commit",
        data={"account_id": account_id, "invert_sign": False, "prefer_mdy": True},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["row_count"] == 3


@pytest.mark.asyncio
async def test_duplicate_upload_rejected(client: AsyncClient) -> None:
    csv_data = (
        "Date,Description,Amount\n"
        "02/01/2026,FIGMA,-15.00\n"
    )
    acc_resp = await client.post("/api/v1/accounts", json={
        "name": "Dupe Test", "type": "checking", "institution": "Test Bank", "mask": "8888"
    })
    account_id = acc_resp.json()["id"]

    files = {"file": ("dupe.csv", io.BytesIO(csv_data.encode()), "text/csv")}
    resp1 = await client.post("/api/v1/imports", files=files)
    assert resp1.status_code == 201
    draft1 = resp1.json()["draft_id"]
    await client.post(f"/api/v1/imports/{draft1}/commit",
                      data={"account_id": account_id})

    # Re-upload same file
    files2 = {"file": ("dupe.csv", io.BytesIO(csv_data.encode()), "text/csv")}
    resp2 = await client.post("/api/v1/imports", files=files2)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_list_transactions(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/transactions?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_review_queue(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/review/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_categories(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    cats = resp.json()
    slugs = [c["id"] for c in cats]
    assert "software" in slugs
    assert "meals" in slugs
    assert "client_income" in slugs


@pytest.mark.asyncio
async def test_reports_summary(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reports/summary?year=2026")
    assert resp.status_code == 200
    data = resp.json()
    assert "schedule_c_lines" in data


@pytest.mark.asyncio
async def test_rules_crud(client: AsyncClient) -> None:
    # Create
    resp = await client.post("/api/v1/rules", json={
        "match_type": "merchant_exact",
        "pattern": "MY CUSTOM VENDOR",
        "category_id": "software",
        "priority": 5,
    })
    assert resp.status_code == 201
    rule_id = resp.json()["id"]

    # List
    resp = await client.get("/api/v1/rules")
    ids = [r["id"] for r in resp.json()]
    assert rule_id in ids

    # Delete
    resp = await client.delete(f"/api/v1/rules/{rule_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_rule_toggle_partial_update(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/rules", json={
        "match_type": "contains", "pattern": "TOGGLE VENDOR",
        "category_id": "software", "priority": 1,
    })
    rule_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/rules/{rule_id}", json={"enabled": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["pattern"] == "TOGGLE VENDOR"

    await client.delete(f"/api/v1/rules/{rule_id}")


@pytest.mark.asyncio
async def test_commit_without_invert_flag_autodetects_card_signs(client: AsyncClient) -> None:
    from pathlib import Path

    sample = Path(__file__).resolve().parents[4] / "sample_data" / "contoso_card.csv"
    acc = await client.post("/api/v1/accounts", json={
        "name": "Card Sign Test", "type": "credit_card", "institution": "Contoso", "mask": "7777"
    })
    draft = await client.post(
        "/api/v1/imports",
        files={"file": ("card_sign_test.csv", io.BytesIO(sample.read_bytes()), "text/csv")},
    )
    if draft.status_code == 409:  # already imported by another test run
        return
    resp = await client.post(
        f"/api/v1/imports/{draft.json()['draft_id']}/commit",
        data={"account_id": acc.json()["id"]},
    )
    assert resp.status_code == 201
    # purchases must be flipped to outflows, so most rows are categorized, not "unknown credit"
    assert resp.json()["auto_count"] > 5
