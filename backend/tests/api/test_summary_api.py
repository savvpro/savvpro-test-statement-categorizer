from fastapi.testclient import TestClient

from tests.api.helpers import by_description, upload_bytes, upload_sample


def totals(summary: dict) -> dict[str, str]:  # type: ignore[type-arg]
    return {c["category_id"]: c["total"] for c in summary["categories"] + summary["non_operating"]}


def test_summary_credit_card_hand_computed(client: TestClient) -> None:
    body = upload_sample(client, "credit_card.csv")
    summary = client.get(f"/api/statements/{body['id']}/summary").json()
    by_cat = totals(summary)

    # Software: 3 months x (59.99 + 15.00 + 10.00 + 14.40)
    assert by_cat["software_subscriptions"] == "-298.17"
    # Travel: 18.72 + 412.60 + 389.22 + 31.05 + 22.40
    assert by_cat["travel"] == "-873.99"
    # Best Buy 129.99 purchase fully reversed by the linked return: nets to zero, not income.
    assert by_cat["equipment"] == "0.00"
    assert "refund" not in by_cat
    # Meals 26.40 + 33.15 = 59.55, deductible at 50% = 29.775 -> 29.78 (half up)
    meals = next(c for c in summary["categories"] if c["category_id"] == "meals")
    assert (meals["total"], meals["deductible"]) == ("-59.55", "29.78")
    # Card payments (1520.44 + 1890.12 + 1650.00) are non-operating: not income, not expense.
    assert by_cat["card_payment"] == "5060.56"
    assert all(c["category_id"] != "card_payment" for c in summary["categories"])

    # 298.17 + 873.99 + 300.00 + 83.70 + 76.41 + 59.55 + 2.62
    assert summary["expenses"] == "1694.44"
    assert summary["estimated_deductible"] == "1664.67"  # 1694.44 - 59.55 + 29.78
    assert summary["income"] == "0.00"
    assert summary["net"] == "-1694.44"
    assert summary["needs_review_count"] == 14
    assert summary["unlinked_refunds"] == "0.00"


def test_unlinked_refund_shown_separately_and_pending_excluded(client: TestClient) -> None:
    content = (
        b"Date,Description,Amount\n"
        b"01/05/2026,REFUND FROM ORBIT GEAR,25.00\n"
        b"01/06/2026,PENDING ADOBE CREATIVE CLOUD,-59.99\n"
        b"01/07/2026,ADOBE CREATIVE CLOUD,-59.99\n"
    )
    body = upload_bytes(client, "mixed.csv", content).json()
    summary = client.get(f"/api/statements/{body['id']}/summary").json()
    assert summary["unlinked_refunds"] == "25.00"
    assert summary["unlinked_refund_count"] == 1
    assert summary["income"] == "0.00"
    assert summary["expenses"] == "59.99"
    assert (summary["pending_count"], summary["pending_amount"]) == (1, "-59.99")


def test_summary_counts_user_confirmed_rows(client: TestClient) -> None:
    body = upload_sample(client, "credit_card.csv")
    bistro = by_description(body, "TST* BLUE FIG BISTRO")[0]
    client.patch(f"/api/transactions/{bistro['id']}", json={"category_id": "meals"})
    summary = client.get(f"/api/statements/{body['id']}/summary").json()
    assert totals(summary)["meals"] == "-124.35"  # 59.55 + 64.80
    assert summary["needs_review_count"] == 13
    assert client.get("/api/statements/999/summary").status_code == 404
