from app.categorizer import categorize_transaction, summarize_transactions
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_refund_takes_precedence_over_merchant_match() -> None:
    result = categorize_transaction({"description": "Adobe refund", "amount": "52.99"})

    assert result["category"] == "Refund"
    assert result["confidence"] == "high"
    assert result["needs_review"] is False


def test_transfer_is_not_spending() -> None:
    result = categorize_transaction({"description": "Transfer to savings", "amount": "500"})

    assert result["category"] == "Transfer"
    assert result["needs_review"] is False


def test_known_merchant_is_software() -> None:
    result = categorize_transaction({"description": "ADOBE CREATIVE CLOUD", "amount": "52.99"})

    assert result["category"] == "Software"
    assert result["confidence"] == "high"


def test_unknown_merchant_needs_review() -> None:
    result = categorize_transaction({"description": "Joes Cafe 9921", "amount": "18.50"})

    assert result["category"] == "Needs Review"
    assert result["needs_review"] is True


def test_ambiguous_description_needs_review() -> None:
    result = categorize_transaction({"description": "Marketing client lunch", "amount": "42"})

    assert result["category"] == "Needs Review"
    assert result["needs_review"] is True


def test_categorize_endpoint_returns_enriched_transactions() -> None:
    response = client.post(
        "/transactions/categorize",
        json={
            "transactions": [
                {"source_row": 2, "date": "2026-01-03", "description": "Figma", "amount": "15"}
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["transactions"][0]["category"] == "Software"


def test_summary_separates_spending_refunds_transfers_and_review() -> None:
    transactions = [
        {"amount": "10", "category": "Software", "needs_review": False},
        {"amount": "5", "category": "Refund", "needs_review": False},
        {"amount": "20", "category": "Transfer", "needs_review": False},
        {"amount": "7", "category": "Needs Review", "needs_review": True},
    ]

    summary = summarize_transactions(transactions)

    assert summary["spending_total"] == "17"
    assert summary["refund_total"] == "5"
    assert summary["transfer_total"] == "20"
    assert summary["review_total"] == "7"
    assert summary["review_count"] == 1


def test_category_update_accepts_user_decision() -> None:
    response = client.put(
        "/transactions/4/category",
        json={"category": "Meals"},
    )

    assert response.status_code == 200
    assert response.json()["needs_review"] is False
    assert response.json()["reason"] == "Category selected by the user."


def test_category_update_rejects_unknown_category() -> None:
    response = client.put(
        "/transactions/4/category",
        json={"category": "Maybe Business"},
    )

    assert response.status_code == 400


def test_export_returns_csv() -> None:
    response = client.post(
        "/transactions/export",
        json={"transactions": [{"source_row": 2, "description": "Figma", "category": "Software"}]},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "categorized-statement.csv"
    assert "source_row,date,description,amount,category" in response.json()["csv"]