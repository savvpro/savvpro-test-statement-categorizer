import pytest
from fastapi.testclient import TestClient

from app.csv_parser import StatementFormatError, parse_statement
from app.main import app

client = TestClient(app)


def _parse(csv_text: str):
    return parse_statement(csv_text.encode("utf-8"))


def test_categorizes_normal_transactions_and_returns_net_totals():
    result = _parse(
        "Date,Description,Amount\n"
        "2025-01-02,WHOLE FOODS MARKET,-45.25\n"
        "01/03/2025,STARBUCKS,-6.50\n"
        "2025-01-04,CLIENT PAYMENT,125.00\n"
    )

    assert [transaction["category"] for transaction in result.transactions] == [
        "Groceries",
        "Dining",
        "Income",
    ]
    assert result.transactions[0]["date"] == "2025-01-02"
    assert result.category_totals["Groceries"] == -45.25
    assert result.category_totals["Dining"] == -6.5
    assert result.category_totals["Income"] == 125.0
    assert result.total_rows == 3
    assert result.invalid_rows == []


def test_normalizes_messy_headers_and_debit_credit_columns():
    result = _parse(
        " Posted Date , Transaction Details , Debit Amount , Credit Amount \n"
        '2025-02-03,"AMAZON PURCHASE","1,234.56",\n'
    )

    assert result.transactions[0]["date"] == "2025-02-03"
    assert result.transactions[0]["description"] == "AMAZON PURCHASE"
    assert result.transactions[0]["amount"] == -1234.56
    assert result.transactions[0]["category"] == "Shopping"


def test_supports_quoted_currency_amounts_and_debit_credit_signs():
    result = _parse(
        " Posted Date , Transaction Details , Debit Amount , Credit Amount \n"
        '2025-02-03,"AMAZON PURCHASE","$45.99",\n'
        '2025-02-04,"PAYROLL DIRECT DEPOSIT",,"$1,234.56"\n'
    )

    assert [(row["amount"], row["category"]) for row in result.transactions] == [
        (-45.99, "Shopping"),
        (1234.56, "Income"),
    ]


def test_unknown_transaction_is_flagged_for_review_not_guessed():
    result = _parse("date,description,amount\n2025-03-01,JOES CAFE 9921,-12.00\n")

    transaction = result.transactions[0]
    assert transaction["category"] == "Needs Review"
    assert transaction["needs_review"] is True
    assert transaction["review_reason"]


def test_refund_is_not_classified_as_income_and_nets_against_category():
    result = _parse(
        "date,description,amount\n"
        "2025-04-01,AMAZON PURCHASE,-40.00\n"
        "2025-04-02,AMAZON REFUND,40.00\n"
        "2025-04-03,REFUND UNKNOWN MERCHANT,10.00\n"
    )

    assert result.transactions[1]["category"] == "Shopping"
    assert result.transactions[1]["transaction_type"] == "refund"
    assert result.transactions[1]["needs_review"] is False
    assert result.transactions[2]["category"] == "Needs Review"
    assert result.transactions[2]["transaction_type"] == "refund"
    assert result.category_totals["Shopping"] == 0


def test_transfers_are_separate_from_spending():
    result = _parse(
        "date,description,amount\n"
        "2025-05-01,TRANSFER TO SAVINGS,-500.00\n"
        "2025-05-02,UBER TRIP,-20.00\n"
    )

    assert result.transactions[0]["category"] == "Transfers"
    assert result.transactions[0]["transaction_type"] == "transfer"
    assert result.transactions[0]["needs_review"] is False
    assert result.category_totals["Transfers"] == -500
    assert result.category_totals["Transport"] == -20


def test_invalid_rows_are_reported_without_dropping_valid_transactions():
    result = _parse(
        "date,description,amount\n"
        "2025-06-01,SAFEWAY,-20.00\n"
        "not-a-date,,not-money\n"
    )

    assert len(result.transactions) == 1
    assert len(result.invalid_rows) == 1
    invalid = result.invalid_rows[0]
    assert invalid["row_number"] == 3
    assert any(error.startswith("date:") for error in invalid["errors"])
    assert any(error.startswith("description:") for error in invalid["errors"])
    assert any(error.startswith("amount:") for error in invalid["errors"])


def test_rejects_csv_without_required_headers():
    with pytest.raises(StatementFormatError, match="date and description"):
        _parse("merchant,total\nAmazon,12.00\n")


def test_api_returns_categorization_and_invalid_rows():
    response = client.post(
        "/categorize",
        files={
            "file": (
                "statement.csv",
                b"Date,Description,Amount\n2025-01-02,UBER TRIP,-14.00\nbad,,nope\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transactions"][0]["category"] == "Transport"
    assert payload["invalid_rows"][0]["row_number"] == 3
    assert payload["category_totals"]["Transport"] == -14


def test_api_rejects_missing_transaction_headers():
    response = client.post(
        "/categorize",
        files={"file": ("statement.csv", b"merchant,total\nAmazon,12.00\n", "text/csv")},
    )

    assert response.status_code == 400
    assert "date and description" in response.json()["detail"]
