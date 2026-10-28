from fastapi.testclient import TestClient

from app.main import app, categorize, parse_money, read_transactions

client = TestClient(app)


def test_known_business_expenses_and_unknown_merchants() -> None:
    csv_data = b"""Date,Description,Amount
2026-01-02,ADOBE CREATIVE CLOUD,-59.99
2026-01-03,UBER TRIP,-24.50
2026-01-04,JOES CAFE 9921,-18.00
"""

    transactions = read_transactions(csv_data)

    assert [row["category"] for row in transactions] == [
        "Software",
        "Travel",
        "Needs review",
    ]
    assert transactions[-1]["status"] == "review"
    assert transactions[0]["amount"] == -59.99


def test_transfers_refunds_and_income_use_specific_rules() -> None:
    assert categorize("TRANSFER TO SAVINGS")[0] == "Transfer"
    assert categorize("ADOBE REFUND")[0] == "Refund"
    assert categorize("CLIENT PAYMENT ACME")[0] == "Income"


def test_parses_parentheses_currency_and_credit_debit_suffixes() -> None:
    assert parse_money("($1,234.56)") == -parse_money("$1,234.56")
    assert parse_money("1,234.56 CR") == parse_money("$1,234.56")
    assert parse_money("45.00 DR") == -parse_money("45.00")


def test_debit_and_credit_columns_normalize_direction() -> None:
    transactions = read_transactions(
        b"Posted Date,Merchant,Debit,Credit\n2026-01-01,STAPLES,42.10,\n"
        b"2026-01-02,CLIENT PAYMENT,,500.00\n"
    )

    assert [row["amount"] for row in transactions] == [-42.1, 500.0]


def test_invalid_csv_has_clear_validation_error() -> None:
    try:
        read_transactions(b"Date,Description,Amount\n2026-01-01,Adobe,not-money\n")
    except ValueError as exc:
        assert "Line 2" in str(exc)
    else:
        raise AssertionError("Invalid amount should be rejected.")


def test_upload_endpoint_returns_categorized_rows() -> None:
    response = client.post(
        "/api/categorize",
        files={
            "file": (
                "statement.csv",
                b"Date,Description,Amount\n2026-01-01,GitHub,-10.00\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["transactions"][0]["category"] == "Software"


def test_upload_endpoint_rejects_non_csv_files() -> None:
    response = client.post(
        "/api/categorize",
        files={"file": ("statement.pdf", b"not a csv", "application/pdf")},
    )

    assert response.status_code == 415
