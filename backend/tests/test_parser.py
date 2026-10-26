from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_parse_statement_returns_normalized_transactions() -> None:
    response = client.post(
        "/statements/parse",
        files={
            "file": (
                "statement.csv",
                "Date,Description,Amount\n2026-01-03,Adobe Creative Cloud,$52.99\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "transactions": [
            {
                "source_row": 2,
                "date": "2026-01-03",
                "description": "Adobe Creative Cloud",
                "amount": "52.99",
            }
        ]
    }


def test_parse_statement_rejects_missing_columns() -> None:
    response = client.post(
        "/statements/parse",
        files={"file": ("statement.csv", "Date,Merchant\n2026-01-03,Adobe\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required column(s): amount, description."


def test_parse_statement_rejects_invalid_amount() -> None:
    response = client.post(
        "/statements/parse",
        files={
            "file": (
                "statement.csv",
                "date,description,amount\n2026-01-03,Adobe,unknown\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Row 2: amount must be a number."