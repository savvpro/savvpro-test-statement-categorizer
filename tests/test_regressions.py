"""Regression coverage for malformed imports and review accounting."""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from backend.categorizer import categorize_transactions
from backend.main import app
from backend.models import ReviewStatus, TransactionType
from backend.parser import parse_csv
from backend.summaries import compute_summary


def categorize(rows):
    raw, _ = parse_csv("Date,Description,Amount\n" + rows)
    return categorize_transactions(raw)[0]


def test_extra_csv_cells_are_skipped_without_crashing():
    rows, warnings = parse_csv(
        "Date,Description,Amount\n2024-01-01,Bad,-10,unexpected\n2024-01-02,Adobe,-20\n"
    )
    assert len(rows) == 1
    assert rows[0].description == "Adobe"
    assert any("extra columns" in warning for warning in warnings)


def test_duplicate_headers_are_rejected():
    with pytest.raises(ValueError, match="Duplicate column"):
        parse_csv("Date,Description,Amount, amount\n2024-01-01,Adobe,-10,-100\n")


@pytest.mark.parametrize("amount", ["1e100000", "-1e100000", "0.001"])
def test_out_of_range_amounts_are_reported(amount):
    rows, warnings = parse_csv(
        f"Date,Description,Amount\n2024-01-01,Bad,{amount}\n2024-01-02,Adobe,-20\n"
    )
    assert len(rows) == 1
    assert warnings


def test_refund_category_totals_do_not_depend_on_row_order():
    rows = categorize("2024-01-02,REFUND ADOBE,20\n2024-01-01,ADOBE,-100\n")
    forward = compute_summary(rows)
    reverse = compute_summary(list(reversed(rows)))
    assert forward.model_dump() == reverse.model_dump()
    assert forward.category_totals["Software"] == Decimal("80")


def test_prior_period_refund_is_not_clamped_to_zero():
    summary = compute_summary(categorize("2024-01-02,REFUND ADOBE,20\n"))
    assert summary.net_expenses == Decimal("-20")
    assert summary.category_totals["Software"] == Decimal("-20")
    assert summary.net_operating_result == Decimal("20")


def test_duplicate_expenses_are_held_out_of_confirmed_totals():
    rows = categorize("2024-01-01,ADOBE,-20\n2024-01-01,ADOBE,-20\n")
    summary = compute_summary(rows)
    assert summary.total_expenses == 0
    assert summary.unclassified_amount == Decimal("40")
    assert summary.needs_review_count == 2


def test_outgoing_refund_for_known_merchant_needs_review():
    row = categorize("2024-01-01,REFUND ADOBE,-20\n")[0]
    assert row.transaction_type == TransactionType.UNKNOWN
    assert row.review_status == ReviewStatus.NEEDS_REVIEW


def test_refund_links_by_merchant_and_date_even_in_descending_statement():
    rows = categorize("2024-01-03,REFUND ADOBE MONTHLY,20\n2024-01-02,FIGMA MONTHLY,-20\n2024-01-01,ADOBE MONTHLY,-20\n")
    assert rows[0].linked_transaction_id == 3


def test_refund_does_not_link_to_future_or_ambiguous_purchase():
    future = categorize("2024-01-02,ADOBE,-20\n2024-01-01,REFUND ADOBE,20\n")
    assert future[1].linked_transaction_id is None
    ambiguous = categorize("2024-01-01,ADOBE,-20\n2024-01-02,ADOBE,-20\n2024-01-03,REFUND ADOBE,20\n")
    assert ambiguous[2].linked_transaction_id is None


def test_confirming_unknown_cannot_make_summary_final():
    row = categorize("2024-01-01,MYSTERY,-20\n")[0]
    row.review_status = ReviewStatus.USER_CONFIRMED
    summary = compute_summary([row])
    assert summary.is_provisional
    assert summary.needs_review_count == 1


@pytest.mark.anyio
async def test_correction_with_contradictory_direction_stays_in_review():
    rows = categorize("2024-01-01,ADOBE,-20\n")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/transactions/correct", json={
            "transaction_id": 1,
            "update": {"transaction_type": "income", "business_category": "Client Income"},
            "transactions": [row.model_dump(mode="json") for row in rows],
        })
    assert response.status_code == 200
    assert response.json()["transactions"][0]["review_status"] == "needs_review"
    assert response.json()["summary"]["total_income"] == "0.00"


@pytest.mark.anyio
async def test_oversize_upload_returns_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/statements/parse", files={
            "file": ("large.csv", b"x" * (5 * 1024 * 1024 + 1), "text/csv")
        })
    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
