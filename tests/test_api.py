"""Integration tests for the FastAPI endpoints."""

import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest.fixture
def sample_csv_bytes() -> bytes:
    path = Path(__file__).resolve().parent.parent / "data" / "sample_statement.csv"
    return path.read_bytes()


@pytest.fixture
def bad_csv_bytes() -> bytes:
    return b"Name,Value\nFoo,Bar\n"


@pytest.mark.anyio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_parse_valid_csv(sample_csv_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/statements/parse",
            files={"file": ("statement.csv", sample_csv_bytes, "text/csv")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "transactions" in data
    assert "summary" in data
    assert len(data["transactions"]) > 0


@pytest.mark.anyio
async def test_parse_invalid_columns(bad_csv_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/statements/parse",
            files={"file": ("bad.csv", bad_csv_bytes, "text/csv")},
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_demo_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["transactions"]) > 0
    assert data["summary"]["transaction_count"] > 0


@pytest.mark.anyio
async def test_correct_transaction_endpoint(sample_csv_bytes):
    """Test dedicated POST /api/transactions/correct endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First parse
        parse_resp = await client.post(
            "/api/statements/parse",
            files={"file": ("statement.csv", sample_csv_bytes, "text/csv")},
        )
        transactions = parse_resp.json()["transactions"]

        # Correct transaction #6 (e.g. Joe's Cafe) to Meals & Entertainment
        correct_resp = await client.post(
            "/api/transactions/correct",
            json={
                "transaction_id": 6,
                "update": {
                    "transaction_type": "expense",
                    "business_category": "Meals & Entertainment",
                },
                "transactions": transactions,
            },
        )

    assert correct_resp.status_code == 200
    data = correct_resp.json()
    corrected_tx = next(t for t in data["transactions"] if t["id"] == 6)
    assert corrected_tx["business_category"] == "Meals & Entertainment"
    assert corrected_tx["review_status"] == "user_corrected"
    assert "Meals & Entertainment" in data["summary"]["category_totals"]


@pytest.mark.anyio
async def test_recalculate_endpoint(sample_csv_bytes):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        parse_resp = await client.post(
            "/api/statements/parse",
            files={"file": ("statement.csv", sample_csv_bytes, "text/csv")},
        )
        transactions = parse_resp.json()["transactions"]

        recalc_resp = await client.post(
            "/api/transactions/recalculate",
            json={"transactions": transactions},
        )
    assert recalc_resp.status_code == 200
    summary = recalc_resp.json()
    assert "total_income" in summary
    assert "net_operating_result" in summary
